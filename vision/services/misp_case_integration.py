import logging
from django.db.models import Q
from django.utils import timezone
from core.models import Observable, Tag
from vision.models import ThreatIntelligenceItem

logger = logging.getLogger(__name__)

class MISPCaseIntegration:
    """
    Service class for integrating MISP threat intelligence with cases
    """
    
    @staticmethod
    def find_threat_intel_for_observable(observable):
        """
        Find threat intelligence data for a given observable
        
        Args:
            observable: Observable instance to find threat intel for
            
        Returns:
            List of ThreatIntelligenceItem objects that match the observable
        """
        # Map observable types to threat intelligence item types
        type_mapping = {
            Observable.IP: 'ip',
            Observable.DOMAIN: 'domain',
            Observable.URL: 'url',
            Observable.EMAIL: 'email',
            Observable.HASH_MD5: 'hash',
            Observable.HASH_SHA1: 'hash',
            Observable.HASH_SHA256: 'hash',
        }
        
        if observable.type not in type_mapping:
            logger.info(f"Observable type {observable.type} not supported for threat intel matching")
            return []
            
        # Get the corresponding threat intelligence item type
        item_type = type_mapping[observable.type]
        
        # Find matching threat intelligence items
        items = ThreatIntelligenceItem.objects.filter(
            item_type=item_type,
            value__iexact=observable.value
        )
        
        if items.exists():
            logger.info(f"Found {items.count()} threat intelligence items for observable {observable.value}")
        
        return items
    
    @staticmethod
    def enrich_case_with_threat_intel(case):
        """
        Enrich a case with threat intelligence data for all its observables
        
        Args:
            case: Case instance to enrich
            
        Returns:
            Dictionary with statistics about enrichment (items_found, observables_enriched)
        """
        stats = {
            'items_found': 0,
            'observables_enriched': 0,
            'tags_added': 0,
            'urls_added': 0,
            'events_processed': 0
        }
        
        observables = case.observables.all()
        
        # Lista para armazenar URLs dos eventos MISP associados aos IOCs
        misp_event_urls = []
        # Lista para armazenar tags MISP a serem adicionadas ao caso
        misp_tags = []
        # Dicionário para acompanhar observables já processados (por url do evento)
        processed_urls = {}
        
        # Verificar se já existe um evento de timeline com URLs do MISP
        existing_event = None
        try:
            existing_events = case.timeline_events.filter(event_type='threat_intel_urls').order_by('-created_at')
            if existing_events.exists():
                existing_event = existing_events.first()
                if 'misp_event_urls' in existing_event.metadata:
                    # Extrair as URLs existentes para evitar duplicação
                    for event_url in existing_event.metadata.get('misp_event_urls', []):
                        if 'url' in event_url:
                            processed_urls[event_url['url']] = True
                            stats['events_processed'] += 1
        except Exception as e:
            logger.error(f"Erro ao processar eventos existentes: {e}")
        
        # Processar todos os observables
        for observable in observables:
            items = MISPCaseIntegration.find_threat_intel_for_observable(observable)
            
            if items:
                stats['items_found'] += items.count()
                stats['observables_enriched'] += 1
                
                # Processar todos os itens de inteligência encontrados, não apenas o de maior confiança
                for item in sorted(items, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x.confidence, 3)):
                    # Atualizar observable com dados de threat intel apenas se for de maior confiança
                    if not hasattr(observable, '_processed_ti') or item.confidence == 'high':
                        observable.is_malicious = item.is_malicious
                        observable.confidence = item.confidence
                        
                        # Map TLP to PAP
                        tlp_to_pap = {
                            'white': Observable.PAP_WHITE,
                            'green': Observable.PAP_GREEN,
                            'amber': Observable.PAP_AMBER,
                            'red': Observable.PAP_RED,
                        }
                        observable.pap = tlp_to_pap.get(item.tlp, Observable.PAP_AMBER)
                        
                        # Add threat intel context to description
                        if observable.description:
                            observable.description += "\n\n"
                        else:
                            observable.description = ""
                        
                        observable.description += f"[Threat Intelligence from {item.feed.name}]\n"
                        observable.description += f"Confidence: {item.get_confidence_display()}\n"
                        
                        # Marcar observable como processado
                        observable._processed_ti = True
                    
                    # Extraindo informações de tags e URLs - sempre processado para todos os itens
                    if item.tags:
                        if not hasattr(observable, '_processed_ti'):
                            observable.description += f"Tags: {item.tags}\n"
                            
                        # Adicionar tags ao caso
                        tag_list = [tag.strip() for tag in item.tags.split(',') if tag.strip()]
                        for tag_name in tag_list:
                            # Verificar se a tag existe no sistema
                            tag, created = Tag.objects.get_or_create(name=tag_name, defaults={'color': 'info'})
                            # Adicionar a tag ao caso se ainda não estiver presente
                            if tag not in case.tags.all():
                                case.tags.add(tag)
                                misp_tags.append(tag_name)
                                stats['tags_added'] += 1
                    
                    if item.creator_org and not hasattr(observable, '_processed_creator'):
                        observable.description += f"Source: {item.creator_org}\n"
                        observable._processed_creator = True
                        
                    if item.description and not hasattr(observable, '_processed_description'):
                        observable.description += f"\n{item.description}\n"
                        observable._processed_description = True
                        
                    # Sempre processar URLs para garantir que todos os eventos sejam capturados
                    if item.external_url:
                        if not hasattr(observable, '_processed_url'):
                            observable.description += f"\nSource Link: {item.external_url}"
                            observable._processed_url = True
                            
                        # Adicionar URL à lista de URLs de eventos MISP se ainda não foi processada
                        if item.external_url not in processed_urls:
                            processed_urls[item.external_url] = True
                            
                            # Tentar extrair o ID do evento da URL se possível
                            event_id = None
                            try:
                                # Formato esperado: "https://localhost/events/view/493"
                                if '/events/view/' in item.external_url:
                                    event_id = item.external_url.split('/events/view/')[-1].split('/')[0]
                            except Exception as e:
                                logger.error(f"Erro ao extrair event_id: {e}")
                                
                            misp_event_urls.append({
                                'url': item.external_url,
                                'feed': item.feed.name,
                                'observed_value': observable.value,
                                'observed_type': observable.get_type_display(),
                                'event_id': event_id,
                                'description': item.description or f"Information from {item.feed.name}",
                                'tags': item.tags,
                                'tlp': item.tlp
                            })
                            stats['urls_added'] += 1
                
                # Salvar observable apenas uma vez após processar todos os itens
                observable.last_seen = timezone.now()
                observable.save()
                
                # Add the enrichment event to the case timeline
                case.add_timeline_event(
                    event_type='threat_intel_added',
                    title=f"Threat Intelligence added to {observable.get_type_display()}: {observable.value}",
                    description=f"Enriched with {items.count()} items of threat intelligence",
                    metadata={
                        'observable_id': observable.id,
                        'feed_names': [item.feed.name for item in items],
                        'is_malicious': any(item.is_malicious for item in items),
                        'tags': misp_tags if misp_tags else []
                    }
                )
        
        # Atualizar o evento existente ou criar um novo evento com as URLs dos eventos MISP
        if misp_event_urls:
            if existing_event:
                # Mesclar os URLs existentes com os novos URLs encontrados
                existing_urls = existing_event.metadata.get('misp_event_urls', [])
                # Criar um mapa de URLs existentes para verificação rápida de duplicação
                existing_url_map = {url_item.get('url'): True for url_item in existing_urls}
                # Adicionar apenas URLs que não existem
                for url_item in misp_event_urls:
                    if url_item.get('url') not in existing_url_map:
                        existing_urls.append(url_item)
                        
                # Atualizar o evento existente
                existing_event.metadata['misp_event_urls'] = existing_urls
                existing_event.save()
            else:
                # Criar um novo evento
                case.add_timeline_event(
                    event_type='threat_intel_urls',
                    title=f"MISP Event URLs for IOCs",
                    description=f"Links para eventos MISP relacionados aos observables deste caso",
                    metadata={
                        'misp_event_urls': misp_event_urls
                    }
                )
        
        # Log de tags adicionadas ao caso
        if misp_tags:
            case.add_timeline_event(
                event_type='threat_intel_tags',
                title=f"MISP Tags Added to Case",
                description=f"Tags de inteligência de ameaças adicionadas a este caso: {', '.join(misp_tags)}",
                metadata={
                    'added_tags': misp_tags
                }
            )
        
        return stats
    
    @staticmethod
    def create_case_from_threat_intel(threat_intel_item, organization, user=None, title=None):
        """
        Create a new case from a threat intelligence item
        
        Args:
            threat_intel_item: ThreatIntelligenceItem to create case from
            organization: Organization to associate the case with
            user: Optional user who is creating the case
            title: Optional custom title for the case (default will use the threat intel item info)
            
        Returns:
            Newly created Case instance
        """
        from cases.models import Case
        
        # Import here to avoid circular imports
        case_title = title if title else f"Threat Intelligence: {threat_intel_item.value}"
        
        # Create a description that includes threat intel details
        description = f"Case automatically created from threat intelligence: {threat_intel_item.value}\n\n"
        description += f"Source: {threat_intel_item.feed.name}\n"
        description += f"Type: {threat_intel_item.get_item_type_display()}\n"
        
        if threat_intel_item.creator_org:
            description += f"Creator Organization: {threat_intel_item.creator_org}\n"
            
        if threat_intel_item.tags:
            description += f"Tags: {threat_intel_item.tags}\n"
            
        if threat_intel_item.description:
            description += f"\nDescription:\n{threat_intel_item.description}\n"
            
        if threat_intel_item.external_url:
            description += f"\nSource Link: {threat_intel_item.external_url}"
        
        # Create the case
        case = Case.objects.create(
            title=case_title,
            description=description,
            organization=organization,
            priority='medium',
            status='open',
            tlp=threat_intel_item.tlp,
            assigned_to=user
        )
        
        # Create an observable from the threat intel
        type_mapping = {
            'ip': Observable.IP,
            'domain': Observable.DOMAIN,
            'url': Observable.URL,
            'hash': Observable.HASH_SHA256,  # Default to SHA256 but we should check the format
            'email': Observable.EMAIL,
            'other': Observable.OTHER
        }
        
        observable_type = type_mapping.get(threat_intel_item.item_type, Observable.OTHER)
        
        # For hash type, try to determine the specific hash type
        if threat_intel_item.item_type == 'hash':
            hash_length = len(threat_intel_item.value.strip())
            if hash_length == 32:
                observable_type = Observable.HASH_MD5
            elif hash_length == 40:
                observable_type = Observable.HASH_SHA1
            elif hash_length == 64:
                observable_type = Observable.HASH_SHA256
        
        # Create the observable
        observable = Observable.objects.create(
            value=threat_intel_item.value,
            type=observable_type,
            confidence=threat_intel_item.confidence,
            is_malicious=threat_intel_item.is_malicious,
            description=f"From threat intelligence source: {threat_intel_item.feed.name}",
            organization=organization,
            last_seen=timezone.now()
        )
        
        # Add the observable to the case
        case.observables.add(observable)
        
        # Add an event to the case timeline
        case.add_timeline_event(
            event_type='created',
            title='Case created from threat intelligence',
            description=f"Case automatically created from {threat_intel_item.feed.name} threat intelligence",
            user=user,
            metadata={
                'threat_intel_id': threat_intel_item.id,
                'feed_name': threat_intel_item.feed.name,
                'observable_id': observable.id
            }
        )
        
        return case 