/**
 * SentinelIQ - JavaScript principal
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar todos os tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializar todos os popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Adicionar classe 'active' aos links de navegação ativos
    const currentLocation = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(function(link) {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });

    // Melhorar formulários com validação
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Adicionar efeito de ripple aos botões
    document.querySelectorAll('.btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            const rect = button.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            
            button.appendChild(ripple);
            
            setTimeout(function() {
                ripple.remove();
            }, 600);
        });
    });

    // Auto-hide para mensagens de alerta após 5 segundos
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeBtn = new bootstrap.Alert(alert);
            closeBtn.close();
        }, 5000);
    });

    // Tornar tabelas responsivas com toggle para colunas em dispositivos móveis
    const tables = document.querySelectorAll('.table-responsive-stack');
    tables.forEach(function(table) {
        const thElements = table.querySelectorAll('th');
        const tdElements = table.querySelectorAll('tbody td');
        
        // Adicionar data-attributes para responsividade
        for (let i = 0; i < thElements.length; i++) {
            const headerText = thElements[i].textContent;
            const cells = table.querySelectorAll(`tbody td:nth-child(${i + 1})`);
            cells.forEach(function(cell) {
                cell.setAttribute('data-label', headerText);
            });
        }
    });

    // Adicionar funcionalidade de busca em tabelas
    document.querySelectorAll('.table-search-input').forEach(function(input) {
        input.addEventListener('keyup', function() {
            const searchText = input.value.toLowerCase();
            const tableId = input.getAttribute('data-table');
            const table = document.getElementById(tableId);
            
            if (table) {
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(function(row) {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchText)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            }
        });
    });

    // Animações ao scroll
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    function checkIfInView() {
        const windowHeight = window.innerHeight;
        const windowTopPosition = window.scrollY;
        const windowBottomPosition = windowTopPosition + windowHeight;
        
        animatedElements.forEach(function(element) {
            const elementHeight = element.offsetHeight;
            const elementTopPosition = element.offsetTop;
            const elementBottomPosition = elementTopPosition + elementHeight;
            
            if (
                (elementBottomPosition >= windowTopPosition) &&
                (elementTopPosition <= windowBottomPosition)
            ) {
                element.classList.add('animated');
            }
        });
    }
    
    window.addEventListener('scroll', checkIfInView);
    checkIfInView(); // Verificar elementos visíveis na carga inicial
});

// Adicionar classe para estilização de campo com foco
document.addEventListener('focusin', function(e) {
    if (e.target.classList.contains('form-control') || e.target.classList.contains('form-select')) {
        const formGroup = e.target.closest('.form-group, .mb-3');
        if (formGroup) {
            formGroup.classList.add('focused');
        }
    }
}, true);

document.addEventListener('focusout', function(e) {
    if (e.target.classList.contains('form-control') || e.target.classList.contains('form-select')) {
        const formGroup = e.target.closest('.form-group, .mb-3');
        if (formGroup) {
            formGroup.classList.remove('focused');
        }
    }
}, true);

// Adicionar funcionalidade de modo escuro
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    
    if (darkModeToggle) {
        // Verificar preferência salva
        const currentTheme = localStorage.getItem('theme');
        
        if (currentTheme) {
            document.documentElement.setAttribute('data-bs-theme', currentTheme);
            
            if (currentTheme === 'dark') {
                darkModeToggle.checked = true;
            }
        }
        
        // Alternar modo escuro ao clicar no toggle
        darkModeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        });
    }
}); 