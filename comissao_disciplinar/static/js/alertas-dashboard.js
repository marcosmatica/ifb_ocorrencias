/**
 * alertas-dashboard.js
 * Gerenciamento de filtros e interações do dashboard de alertas
 */

class AlertasDashboard {
    constructor() {
        this.mesSelector = document.getElementById('mes-selector');
        this.mesSelector2 = document.getElementById('mes-selector-2');
        this.hiddenMes = document.getElementById('hidden-mes');
        this.filterForm = document.getElementById('filter-form');

        this.init();
    }

    init() {
        this.setupTooltips();
        this.setupMesSelectors();
        this.setupFilterForm();
        this.setupPaginationLinks();
        this.setupRemoveFilters();
        this.highlightActiveMonth();
        this.addDebugInfo();
    }

    /**
     * Configurar tooltips do Bootstrap
     */
    setupTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"]')
        );
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Configurar seletores de mês
     */
    setupMesSelectors() {
        // Seletor principal (superior)
        if (this.mesSelector) {
            this.mesSelector.addEventListener('change', (e) => {
                const selectedMonth = e.target.value;
                console.log('Mês selecionado (principal):', selectedMonth);
                this.updateUrlWithMonth(selectedMonth);
            });
        }

        // Seletor secundário (filtros)
        if (this.mesSelector2) {
            this.mesSelector2.addEventListener('change', (e) => {
                const selectedMonth = e.target.value;
                console.log('Mês selecionado (filtros):', selectedMonth);
                if (this.hiddenMes) {
                    this.hiddenMes.value = selectedMonth;
                }
            });
        }

        // Sincronizar valores iniciais
        this.syncMesSelectors();
    }

    /**
     * Sincronizar valores dos seletores de mês
     */
    syncMesSelectors() {
        const urlParams = new URLSearchParams(window.location.search);
        const mesParam = urlParams.get('mes');

        if (mesParam) {
            if (this.mesSelector) {
                this.mesSelector.value = mesParam;
            }
            if (this.mesSelector2) {
                this.mesSelector2.value = mesParam;
            }
            if (this.hiddenMes) {
                this.hiddenMes.value = mesParam;
            }
        }
    }

    /**
     * Configurar formulário de filtros
     */
    setupFilterForm() {
        if (this.filterForm) {
            this.filterForm.addEventListener('submit', (e) => {
                // Garantir que o mês oculto está atualizado
                if (this.mesSelector2 && this.hiddenMes) {
                    this.hiddenMes.value = this.mesSelector2.value;
                }
                console.log('Formulário enviado com mês:', this.hiddenMes.value);
            });
        }
    }

    /**
     * Atualizar URL mantendo parâmetros existentes
     */
    updateUrlWithMonth(month) {
        const url = new URL(window.location.href);
        const params = new URLSearchParams(url.search);

        // Obter valores atuais dos filtros
        const currentTurma = params.get('turma') || '';
        const currentTipo = params.get('tipo') || '';

        // Construir nova URL mantendo filtros existentes
        let newUrl = `${url.pathname}?mes=${month}`;
        if (currentTurma) newUrl += `&turma=${currentTurma}`;
        if (currentTipo) newUrl += `&tipo=${currentTipo}`;

        console.log('Redirecionando para:', newUrl);

        // Redirecionar
        window.location.href = newUrl;
    }

    /**
     * Atualizar links de paginação com parâmetros atuais
     */
    setupPaginationLinks() {
        const urlParams = new URLSearchParams(window.location.search);
        const currentMonth = urlParams.get('mes');
        const currentTurma = urlParams.get('turma');
        const currentTipo = urlParams.get('tipo');

        const paginationLinks = document.querySelectorAll('.pagination a');
        paginationLinks.forEach(link => {
            const url = new URL(link.href);

            // Adicionar parâmetros se existirem
            if (currentMonth) url.searchParams.set('mes', currentMonth);
            if (currentTurma) url.searchParams.set('turma', currentTurma);
            if (currentTipo) url.searchParams.set('tipo', currentTipo);

            link.href = url.toString();
        });
    }

    /**
     * Configurar remoção de filtros
     */
    setupRemoveFilters() {
        document.querySelectorAll('.remove-filter').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Removendo filtro:', this.href);
                window.location.href = this.href;
            });
        });
    }

    /**
     * Destacar mês ativo nos dropdowns
     */
    highlightActiveMonth() {
        const urlParams = new URLSearchParams(window.location.search);
        const currentMonth = urlParams.get('mes');

        if (currentMonth) {
            // Destacar no seletor principal
            if (this.mesSelector) {
                const options = this.mesSelector.querySelectorAll('option');
                options.forEach(option => {
                    if (option.value === currentMonth) {
                        option.classList.add('month-active');
                        option.setAttribute('selected', 'selected');
                    } else {
                        option.classList.remove('month-active');
                    }
                });
            }

            // Destacar no seletor secundário
            if (this.mesSelector2) {
                const options = this.mesSelector2.querySelectorAll('option');
                options.forEach(option => {
                    if (option.value === currentMonth) {
                        option.classList.add('month-active');
                        option.setAttribute('selected', 'selected');
                    } else {
                        option.classList.remove('month-active');
                    }
                });
            }
        }
    }

    /**
     * Adicionar informações de debug no console
     */
    addDebugInfo() {
        const urlParams = new URLSearchParams(window.location.search);
        console.log('=== DEBUG ALERTAS DASHBOARD ===');
        console.log('Mês (URL):', urlParams.get('mes'));
        console.log('Turma (URL):', urlParams.get('turma'));
        console.log('Tipo (URL):', urlParams.get('tipo'));
        console.log('Página (URL):', urlParams.get('page'));
        console.log('Mês Selector 1:', this.mesSelector?.value);
        console.log('Mês Selector 2:', this.mesSelector2?.value);
        console.log('Mês Hidden:', this.hiddenMes?.value);
        console.log('==============================');
    }
}

/**
 * Utilitários para gerenciamento de URL
 */
class URLManager {
    /**
     * Obter parâmetro da URL
     */
    static getParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    /**
     * Atualizar parâmetro na URL
     */
    static setParam(param, value) {
        const url = new URL(window.location.href);
        url.searchParams.set(param, value);
        return url.toString();
    }

    /**
     * Remover parâmetro da URL
     */
    static removeParam(param) {
        const url = new URL(window.location.href);
        url.searchParams.delete(param);
        return url.toString();
    }

    /**
     * Obter todos os parâmetros
     */
    static getAllParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const params = {};
        for (const [key, value] of urlParams) {
            params[key] = value;
        }
        return params;
    }
}

/**
 * Confirmação para ações críticas
 */
class ConfirmationHandler {
    static setupRecalcularButton() {
        const recalcularBtn = document.querySelector('a[href*="recalcular=true"]');
        if (recalcularBtn) {
            recalcularBtn.addEventListener('click', function(e) {
                const confirmed = confirm(
                    'Tem certeza que deseja recalcular os alertas para este mês?\n\n' +
                    'Esta ação irá:\n' +
                    '- Limpar alertas existentes\n' +
                    '- Recalcular baseado nas configurações atuais\n' +
                    '- Pode levar alguns segundos'
                );

                if (!confirmed) {
                    e.preventDefault();
                }
            });
        }
    }
}

/**
 * Melhorias visuais para tabela
 */
class TableEnhancements {
    static init() {
        this.addRowHoverEffect();
        this.addClickableRows();
    }

    static addRowHoverEffect() {
        const tableRows = document.querySelectorAll('.table-hover tbody tr');
        tableRows.forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(52, 152, 219, 0.05)';
            });
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    }

    static addClickableRows() {
        const tableRows = document.querySelectorAll('.table-hover tbody tr');
        tableRows.forEach(row => {
            const viewBtn = row.querySelector('.btn-outline-primary');
            if (viewBtn) {
                row.style.cursor = 'pointer';
                row.addEventListener('click', function(e) {
                    // Não redirecionar se clicou em um botão
                    if (!e.target.closest('.btn-group')) {
                        viewBtn.click();
                    }
                });
            }
        });
    }
}

/**
 * Inicialização quando DOM estiver pronto
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Alertas Dashboard...');

    // Inicializar dashboard principal
    const dashboard = new AlertasDashboard();

    // Configurar confirmações
    ConfirmationHandler.setupRecalcularButton();

    // Melhorar tabela
    TableEnhancements.init();

    console.log('Alertas Dashboard inicializado com sucesso!');
});

/**
 * Exportar para uso global se necessário
 */
window.AlertasDashboard = AlertasDashboard;
window.URLManager = URLManager;