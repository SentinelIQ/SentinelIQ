/**
 * MITRE ATT&CK Tooltips/Popovers
 * 
 * Este script inicializa popovers para elementos MITRE ATT&CK (táticas, técnicas, subtécnicas)
 * e carrega detalhes via AJAX quando o usuário clica em um elemento.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Seleciona todos os badges MITRE
    const badgeElements = document.querySelectorAll('.mitre-badge');
    
    // Para cada badge
    badgeElements.forEach(function(badge) {
        // Adicionar evento de clique diretamente
        badge.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Obter dados do elemento
            const mitreType = badge.getAttribute('data-mitre-type');
            const mitreId = badge.getAttribute('data-mitre-id');
            
            // Se já existir um popover, destrua-o
            if (badge._popover) {
                badge._popover.dispose();
            }
            
            // Crie um novo popover com conteúdo de carregamento
            badge._popover = new bootstrap.Popover(badge, {
                html: true,
                content: '<div class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Carregando...</div>',
                sanitize: false,
                trigger: 'manual'
            });
            
            // Mostre o popover
            badge._popover.show();
            
            // Carregue os dados AJAX
            fetchMitreDetails(mitreType, mitreId)
                .then(data => {
                    // Quando os dados chegarem, atualiza o conteúdo e recria o popover
                    const content = createMitrePopoverContent(mitreType, data);
                    
                    // Destruir o popover antigo
                    badge._popover.dispose();
                    
                    // Criar um novo popover com o conteúdo atualizado
                    badge._popover = new bootstrap.Popover(badge, {
                        html: true,
                        content: content,
                        sanitize: false,
                        trigger: 'manual'
                    });
                    
                    // Mostrar o novo popover
                    badge._popover.show();
                })
                .catch(error => {
                    console.error('Erro ao carregar detalhes MITRE:', error);
                    
                    // Destruir o popover antigo
                    badge._popover.dispose();
                    
                    // Criar um novo popover com mensagem de erro
                    badge._popover = new bootstrap.Popover(badge, {
                        html: true,
                        content: '<div class="text-danger"><i class="fas fa-exclamation-circle me-1"></i> Erro ao carregar detalhes</div>',
                        sanitize: false,
                        trigger: 'manual'
                    });
                    
                    // Mostrar o novo popover
                    badge._popover.show();
                });
        });
        
        // Fechar popover ao clicar em outro lugar
        document.addEventListener('click', function(e) {
            if (badge._popover && !badge.contains(e.target)) {
                badge._popover.hide();
            }
        });
    });
});

/**
 * Busca detalhes de um elemento MITRE ATT&CK via AJAX
 * @returns {Promise} - Promessa com os dados JSON
 */
function fetchMitreDetails(type, id) {
    // Define a URL da API com base no tipo
    let apiUrl;
    
    switch(type) {
        case 'tactic':
            apiUrl = `/api/mitre/tactic/${id}/`;
            break;
        case 'technique':
            apiUrl = `/api/mitre/technique/${id}/`;
            break;
        case 'subtechnique':
            apiUrl = `/api/mitre/subtechnique/${id}/`;
            break;
        default:
            return Promise.reject('Tipo MITRE desconhecido: ' + type);
    }
    
    // Faz a requisição AJAX
    return fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na resposta: ' + response.status);
            }
            return response.json();
        });
}

/**
 * Cria o conteúdo HTML para o popover com base nos dados recebidos
 */
function createMitrePopoverContent(type, data) {
    let content = '<div class="mitre-popover">';
    
    // Título
    if (type === 'tactic') {
        content += `<h6 class="fw-bold">${data.tactic_id}: ${data.name}</h6>`;
    } else if (type === 'technique') {
        content += `<h6 class="fw-bold">${data.technique_id}: ${data.name}</h6>`;
    } else if (type === 'subtechnique') {
        content += `<h6 class="fw-bold">${data.sub_technique_id}: ${data.name}</h6>`;
    }
    
    // Descrição (limitada a ~200 caracteres)
    if (data.description) {
        const shortDesc = data.description.length > 200 
            ? data.description.substring(0, 200) + '...' 
            : data.description;
        
        content += `<p class="small mb-2">${shortDesc}</p>`;
    } else {
        content += '<p class="small text-muted mb-2">Sem descrição disponível</p>';
    }
    
    // Relacionamentos
    if (type === 'technique' && data.tactics && data.tactics.length > 0) {
        content += '<p class="small mb-1 fw-bold">Táticas relacionadas:</p>';
        content += '<div class="mb-2">';
        data.tactics.forEach(tactic => {
            content += `<span class="badge bg-primary me-1 mb-1">${tactic.tactic_id}</span>`;
        });
        content += '</div>';
    } else if (type === 'subtechnique' && data.parent_technique) {
        content += '<p class="small mb-1 fw-bold">Técnica pai:</p>';
        content += `<span class="badge bg-success me-1 mb-2">${data.parent_technique.technique_id}</span>`;
    }
    
    // Link para documentação MITRE
    if (data.url) {
        content += `<div class="mt-2">
            <a href="${data.url}" target="_blank" class="btn btn-sm btn-outline-primary w-100">
                <i class="fas fa-external-link-alt me-1"></i> Ver no MITRE ATT&CK
            </a>
        </div>`;
    }
    
    content += '</div>';
    return content;
} 