import json
import logging
from datetime import datetime, timedelta
import requests
from django.utils import timezone
from django.conf import settings

from vision.models import ThreatIntelligenceItem, MISPTag, MISPGalaxy, MISPCluster

logger = logging.getLogger(__name__)


class MISPService:
    """
    Serviço para interagir com a API do MISP
    """
    
    def __init__(self, misp_instance):
        """
        Inicializa o serviço com uma instância de MISPInstance
        """
        self.misp = misp_instance
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.misp.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        self.session.verify = self.misp.verify_ssl
        self.base_url = self.misp.url.rstrip('/')
    
    def _request(self, endpoint, method='GET', params=None, data=None):
        """
        Realiza uma requisição para a API do MISP
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            logger.info(f"Making {method} request to {url}")
            if params:
                logger.info(f"Request params: {params}")

            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Method {method} not supported")
            
            response.raise_for_status()
            json_response = response.json()
            
            # Log the response structure for debugging
            if isinstance(json_response, dict):
                logger.info(f"Response is a dictionary with keys: {list(json_response.keys())}")
            elif isinstance(json_response, list):
                logger.info(f"Response is a list with {len(json_response)} items")
                if json_response and isinstance(json_response[0], dict):
                    logger.info(f"First item keys: {list(json_response[0].keys())}")
            
            return json_response
        except requests.RequestException as e:
            logger.error(f"MISP API error: {str(e)}", exc_info=True)
            raise Exception(f"MISP API error: {str(e)}")
        except ValueError as e:
            logger.error(f"JSON parsing error: {str(e)}", exc_info=True)
            raise Exception(f"JSON parsing error: {str(e)}")
    
    def get_recent_events(self):
        """
        Obtém eventos recentes do MISP
        """
        days = self.misp.import_from_days
        
        # Se days for 0, obter todos os eventos
        if days == 0:
            params = {'limit': 100}  # Limitar para evitar carregar muitos dados
        else:
            # Calcular data para filtrar eventos
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            params = {
                'limit': 100,
                'from': from_date
            }
        
        # Adicionar filtros de tags se especificados
        tags_include = []
        if self.misp.tags_to_include:
            tags_include = [tag.strip() for tag in self.misp.tags_to_include.split(',') if tag.strip()]
        
        tags_exclude = []
        if self.misp.tags_to_exclude:
            tags_exclude = [tag.strip() for tag in self.misp.tags_to_exclude.split(',') if tag.strip()]
        
        if tags_include:
            params['tags'] = tags_include
        
        # Obter eventos
        events_data = self._request('events/index', params=params)
        
        # Log the response type for debugging
        logger.info(f"MISP events response type: {type(events_data)}")
        
        # Check if events_data is already a list
        if isinstance(events_data, list):
            events = events_data
        else:
            # Otherwise, it should be a dictionary with a 'response' key
            events = events_data.get('response', [])
        
        # Filtrar eventos por tags a excluir
        if tags_exclude:
            filtered_events = []
            for event in events:
                if 'Tag' in event:
                    event_tags = [tag['name'] for tag in event['Tag']]
                    if not any(tag in event_tags for tag in tags_exclude):
                        filtered_events.append(event)
                else:
                    filtered_events.append(event)
            events = filtered_events
        
        return events
    
    def get_event_details(self, event_id):
        """
        Obtém detalhes de um evento específico incluindo seus atributos
        """
        # Define additional parameters to include in the request
        params = {
            "include_galaxy": True,
            "include_event_tags": True,
            "include_correlations": True,
            "include_context": True,
            "include_sightings": True,
            "sg_reference_only": True,
            "page": 1,
            "limit": 500,
        }
        
        response = self._request(f'events/view/{event_id}', params=params)
        
        # Check if the response is a list instead of a dictionary
        if isinstance(response, list):
            # If it's a list, take the first item if available
            if response and len(response) > 0:
                return response[0]
            else:
                # Return an empty dict with Event key to prevent errors
                return {"Event": {}}
        
        # Verificar se precisamos obter correlações adicionalmente
        if isinstance(response, dict) and 'Event' in response:
            # Se não houver informações de correlação, tentar obter
            if 'RelatedEvent' not in response['Event']:
                try:
                    logger.info(f"Fetching correlations for event ID: {event_id}")
                    correlations = self._request(f'events/{event_id}/relatedevent')
                    
                    # Adicionar as correlações ao evento
                    if isinstance(correlations, dict) and 'response' in correlations:
                        response['Event']['RelatedEvent'] = correlations['response']
                    elif isinstance(correlations, list):
                        response['Event']['RelatedEvent'] = correlations
                except Exception as e:
                    logger.warning(f"Error fetching correlations for event ID {event_id}: {str(e)}")
                    response['Event']['RelatedEvent'] = []
        
        return response
    
    def get_tags(self):
        """
        Obtém todas as tags disponíveis no MISP
        """
        try:
            logger.info("Fetching all MISP tags")
            tags_data = self._request('tags')
            
            if isinstance(tags_data, list):
                return tags_data
            elif isinstance(tags_data, dict) and 'Tag' in tags_data:
                return tags_data['Tag']
            elif isinstance(tags_data, dict) and 'response' in tags_data:
                if isinstance(tags_data['response'], list):
                    return tags_data['response']
                elif isinstance(tags_data['response'], dict) and 'Tag' in tags_data['response']:
                    return tags_data['response']['Tag']
            return []
        except Exception as e:
            logger.error(f"Error fetching MISP tags: {str(e)}", exc_info=True)
            return []
    
    def get_galaxies(self):
        """
        Obtém todos os clusters de galáxias disponíveis no MISP
        """
        try:
            logger.info("Fetching all MISP galaxies/clusters")
            galaxies_data = self._request('galaxies')
            
            if isinstance(galaxies_data, list):
                return galaxies_data
            elif isinstance(galaxies_data, dict) and 'Galaxy' in galaxies_data:
                return galaxies_data['Galaxy']
            elif isinstance(galaxies_data, dict) and 'response' in galaxies_data:
                if isinstance(galaxies_data['response'], list):
                    return galaxies_data['response']
                elif isinstance(galaxies_data['response'], dict) and 'Galaxy' in galaxies_data['response']:
                    return galaxies_data['response']['Galaxy']
            return []
        except Exception as e:
            logger.error(f"Error fetching MISP galaxies: {str(e)}", exc_info=True)
            return []
    
    def get_galaxy_clusters(self, galaxy_id):
        """
        Obtém os clusters de uma galáxia específica
        """
        try:
            logger.info(f"Fetching clusters for galaxy ID: {galaxy_id}")
            clusters_data = self._request(f'galaxies/view/{galaxy_id}')
            
            if isinstance(clusters_data, dict) and 'GalaxyCluster' in clusters_data:
                return clusters_data['GalaxyCluster']
            elif isinstance(clusters_data, list) and len(clusters_data) > 0:
                if isinstance(clusters_data[0], dict) and 'GalaxyCluster' in clusters_data[0]:
                    return clusters_data[0]['GalaxyCluster']
            return []
        except Exception as e:
            logger.error(f"Error fetching clusters for galaxy {galaxy_id}: {str(e)}", exc_info=True)
            return []
    
    def _create_or_update_tag(self, tag_data):
        """
        Cria ou atualiza um registro de tag MISP
        """
        tag_id = str(tag_data.get('id'))
        tag_name = tag_data.get('name')
        
        if not tag_id or not tag_name:
            logger.warning("Tag data incomplete, skipping")
            return None
        
        try:
            tag = MISPTag.objects.get(
                feed=self.misp,
                external_id=tag_id
            )
        except MISPTag.DoesNotExist:
            tag = MISPTag(
                feed=self.misp,
                external_id=tag_id
            )
            
        # Atualizar campos
        tag.name = tag_name
        tag.colour = tag_data.get('colour', '')
        tag.is_hidden = tag_data.get('hide_tag', False)
        tag.is_system = tag_name.startswith('misp-galaxy:') or tag_name.startswith('tlp:')
        
        tag.save()
        return tag
    
    def _create_or_update_galaxy(self, galaxy_data):
        """
        Cria ou atualiza um registro de galáxia MISP
        """
        galaxy_id = str(galaxy_data.get('id'))
        galaxy_name = galaxy_data.get('name')
        
        if not galaxy_id or not galaxy_name:
            logger.warning("Galaxy data incomplete, skipping")
            return None
            
        try:
            galaxy = MISPGalaxy.objects.get(
                feed=self.misp,
                external_id=galaxy_id
            )
        except MISPGalaxy.DoesNotExist:
            galaxy = MISPGalaxy(
                feed=self.misp,
                external_id=galaxy_id
            )
            
        # Atualizar campos
        galaxy.name = galaxy_name
        galaxy.type = galaxy_data.get('type', '')
        galaxy.description = galaxy_data.get('description', '')
        galaxy.version = galaxy_data.get('version', '')
        
        galaxy.save()
        return galaxy
        
    def _create_or_update_cluster(self, cluster_data, galaxy):
        """
        Cria ou atualiza um registro de cluster MISP
        """
        cluster_id = str(cluster_data.get('id'))
        cluster_value = cluster_data.get('value')
        
        if not cluster_id or not cluster_value:
            logger.warning("Cluster data incomplete, skipping")
            return None
            
        try:
            cluster = MISPCluster.objects.get(
                galaxy=galaxy,
                external_id=cluster_id
            )
        except MISPCluster.DoesNotExist:
            cluster = MISPCluster(
                galaxy=galaxy,
                external_id=cluster_id
            )
            
        # Atualizar campos
        cluster.value = cluster_value
        cluster.description = cluster_data.get('description', '')
        cluster.source = cluster_data.get('source', '')
        cluster.uuid = cluster_data.get('uuid', '')
        
        # Salvar metadados adicionais se existirem
        meta_dict = {}
        for meta_key in ['meta', 'metadata', 'synonyms', 'refs', 'related']:
            if cluster_data.get(meta_key):
                meta_dict[meta_key] = cluster_data.get(meta_key)
                
        if meta_dict:
            cluster.meta = meta_dict
            
        cluster.save()
        return cluster
    
    def sync(self):
        """
        Sincroniza dados do MISP para o banco de dados local
        Retorna o número de itens importados/atualizados
        """
        items_imported = 0
        
        try:
            # Obter eventos recentes
            logger.info(f"Fetching recent events from MISP instance: {self.misp.name}")
            events = self.get_recent_events()
            logger.info(f"Retrieved {len(events)} events from MISP")
            
            # Obter todas as tags (opcional - dependendo do uso)
            if self.misp.import_tags:
                logger.info("Importing tags from MISP")
                tags = self.get_tags()
                logger.info(f"Retrieved {len(tags)} tags from MISP")
                
                for tag in tags:
                    try:
                        self._create_or_update_tag(tag)
                        items_imported += 1
                    except Exception as tag_error:
                        logger.error(f"Error processing tag: {str(tag_error)}")
            
            # Obter todas as galáxias e clusters (opcional - dependendo do uso)
            if self.misp.import_galaxies:
                logger.info("Importing galaxies/clusters from MISP")
                galaxies = self.get_galaxies()
                logger.info(f"Retrieved {len(galaxies)} galaxies from MISP")
                
                for galaxy_data in galaxies:
                    try:
                        galaxy_id = galaxy_data.get('id')
                        if galaxy_id:
                            # Criar/atualizar a galáxia
                            galaxy = self._create_or_update_galaxy(galaxy_data)
                            if galaxy:
                                items_imported += 1
                                
                                # Obter e processar clusters para esta galáxia
                                clusters = self.get_galaxy_clusters(galaxy_id)
                                logger.info(f"Retrieved {len(clusters)} clusters for galaxy {galaxy_data.get('name', 'Unknown')}")
                                
                                for cluster_data in clusters:
                                    try:
                                        cluster = self._create_or_update_cluster(cluster_data, galaxy)
                                        if cluster:
                                            items_imported += 1
                                    except Exception as cluster_error:
                                        logger.error(f"Error processing cluster: {str(cluster_error)}")
                    except Exception as galaxy_error:
                        logger.error(f"Error processing galaxy: {str(galaxy_error)}")
            
            # Processar eventos como antes
            for event in events:
                try:
                    event_id = event.get('id')
                    if not event_id:
                        logger.warning("Skipping event without ID")
                        continue
                    
                    logger.info(f"Processing event ID: {event_id}")
                    
                    # Obter detalhes completos do evento
                    event_details = self.get_event_details(event_id)
                    
                    if not event_details:
                        logger.warning(f"No details found for event ID: {event_id}")
                        continue
                    
                    if 'Event' not in event_details:
                        logger.warning(f"Event data not found in response for event ID: {event_id}")
                        continue
                    
                    event_data = event_details['Event']
                    
                    # Criar registro de evento como um item de inteligência
                    logger.info(f"Creating/updating event item for ID: {event_id}")
                    event_item = self._create_or_update_event_item(event_data)
                    items_imported += 1
                    
                    # Processar atributos se configurado
                    if self.misp.import_attributes:
                        attributes = event_data.get('Attribute', [])
                        logger.info(f"Processing {len(attributes)} attributes for event ID: {event_id}")
                        
                        for attr in attributes:
                            try:
                                attribute_item = self._create_or_update_attribute_item(attr, event_data)
                                if attribute_item:
                                    items_imported += 1
                            except Exception as attr_error:
                                logger.error(f"Error processing attribute: {str(attr_error)}")
                                # Continue with next attribute
                                continue
                except Exception as event_error:
                    logger.error(f"Error processing event: {str(event_error)}")
                    # Continue with next event
                    continue
            
            logger.info(f"MISP sync completed. Items imported/updated: {items_imported}")
            return items_imported
        
        except Exception as e:
            logger.error(f"Error synchronizing MISP data: {str(e)}", exc_info=True)
            raise
    
    def _create_or_update_event_item(self, event_data):
        """
        Cria ou atualiza um item de inteligência para um evento MISP
        """
        event_id = event_data.get('id')
        event_info = event_data.get('info', 'No information')
        
        # Verificar se o evento já existe
        try:
            item = ThreatIntelligenceItem.objects.get(
                feed=self.misp,
                item_type='event',
                external_id=str(event_id)
            )
        except ThreatIntelligenceItem.DoesNotExist:
            item = ThreatIntelligenceItem(
                feed=self.misp,
                item_type='event',
                external_id=str(event_id),
                first_seen=timezone.now()
            )
        
        # Extrair tags
        tags = []
        if 'Tag' in event_data:
            tags = [tag.get('name') for tag in event_data['Tag'] if tag.get('name')]
        
        # Determinar TLP baseado nas tags
        tlp = 'amber'  # TLP padrão
        for tag in tags:
            if 'tlp:white' in tag.lower():
                tlp = 'white'
                break
            elif 'tlp:green' in tag.lower():
                tlp = 'green'
                break
            elif 'tlp:amber' in tag.lower():
                tlp = 'amber'
                break
            elif 'tlp:red' in tag.lower():
                tlp = 'red'
                break
        
        # Atualizar campos
        item.value = event_info
        item.description = event_data.get('analysis', '') 
        item.tags = ','.join(tags)
        item.tlp = tlp
        item.is_malicious = True
        item.confidence = 'medium'
        item.external_url = f"{self.misp.url}/events/view/{event_id}"
        item.last_seen = timezone.now()
        
        # Extrair e armazenar informações adicionais
        # Creator Organization
        if 'Orgc' in event_data:
            item.creator_org = event_data['Orgc'].get('name', '')
            
        # Owner Organization
        if 'Org' in event_data:
            item.owner_org = event_data['Org'].get('name', '')
            
        # Event Date
        if 'date' in event_data:
            try:
                # Formato esperado: YYYY-MM-DD
                item.event_date = datetime.strptime(event_data['date'], '%Y-%m-%d')
            except (ValueError, TypeError):
                # Se a data estiver em formato inválido, usar null
                item.event_date = None
                
        # Distribution
        if 'distribution' in event_data:
            dist_value = event_data['distribution']
            dist_mapping = {
                '0': 'Your organization only',
                '1': 'This community only',
                '2': 'Connected communities',
                '3': 'All communities',
                '4': 'Custom sharing group'
            }
            item.distribution = dist_mapping.get(str(dist_value), str(dist_value))
            
        # Número de atributos
        if 'Attribute' in event_data:
            item.attribute_count = len(event_data['Attribute'])
            
        # Creator User
        if 'owner' in event_data:
            item.creator_user = event_data['owner']
            
        # Número de correlações (pode não estar disponível diretamente)
        if 'RelatedEvent' in event_data:
            item.correlation_count = len(event_data['RelatedEvent'])
        
        # Adicionar contexto
        context_data = {
            'event_id': event_id,
            'orgc': event_data.get('Orgc', {}).get('name', 'Unknown'),
            'date': event_data.get('date', ''),
            'threat_level': event_data.get('threat_level_id', ''),
            'analysis': event_data.get('analysis', ''),
            'distribution': event_data.get('distribution', ''),
            'published': event_data.get('published', False)
        }
        item.description += "\n\nContext: " + json.dumps(context_data, indent=2)
        
        item.save()
        return item
    
    def _create_or_update_attribute_item(self, attribute, event_data):
        """
        Cria ou atualiza um item de inteligência para um atributo MISP
        """
        attr_id = attribute.get('id')
        attr_type = attribute.get('type')
        attr_value = attribute.get('value')
        
        if not attr_id or not attr_type or not attr_value:
            return None
        
        # Mapear tipos de atributos MISP para tipos de itens
        type_mapping = {
            'ip-src': 'ip',
            'ip-dst': 'ip',
            'domain': 'domain',
            'hostname': 'domain',
            'email-src': 'email',
            'email-dst': 'email',
            'url': 'url',
            'md5': 'hash',
            'sha1': 'hash',
            'sha256': 'hash',
            'filename|md5': 'hash',
            'filename|sha1': 'hash',
            'filename|sha256': 'hash',
        }
        
        item_type = type_mapping.get(attr_type, 'other')
        
        # Verificar se o atributo já existe
        try:
            item = ThreatIntelligenceItem.objects.get(
                feed=self.misp,
                item_type=item_type,
                value=attr_value,
                external_id=str(attr_id)
            )
        except ThreatIntelligenceItem.DoesNotExist:
            item = ThreatIntelligenceItem(
                feed=self.misp,
                item_type=item_type,
                value=attr_value,
                external_id=str(attr_id),
                first_seen=timezone.now()
            )
        
        # Extrair tags do atributo
        tags = []
        if 'Tag' in attribute:
            tags = [tag.get('name') for tag in attribute['Tag'] if tag.get('name')]
        
        # Determinar TLP baseado nas tags
        tlp = 'amber'  # TLP padrão
        for tag in tags:
            if 'tlp:white' in tag.lower():
                tlp = 'white'
                break
            elif 'tlp:green' in tag.lower():
                tlp = 'green'
                break
            elif 'tlp:amber' in tag.lower():
                tlp = 'amber'
                break
            elif 'tlp:red' in tag.lower():
                tlp = 'red'
                break
        
        # Atualizar campos
        item.description = f"Attribute Type: {attr_type}\n"
        if attribute.get('comment'):
            item.description += f"Comment: {attribute.get('comment')}\n"
        
        item.description += f"\nFrom Event: {event_data.get('info', 'No information')}"
        item.tags = ','.join(tags)
        item.tlp = tlp
        item.is_malicious = True
        item.confidence = 'medium'
        item.external_url = f"{self.misp.url}/events/view/{event_data.get('id')}"
        item.last_seen = timezone.now()
        
        item.save()
        return item 