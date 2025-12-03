/**
 * alertas-dashboard.js - Versão Otimizada
 * Gerenciamento de filtros e interações do dashboard de alertas
 */

class AlertasDashboard {
    constructor() {
        this.initializeElements();
        this.init();
    }

    initializeElements() {
        this.mesSelector = document.getElementById('mes-selector');
        this.mesSelector2 = document.getElementById('mes-selector-2');
        this.hiddenMes = document.getElementById('hidden-mes');
        this.filterForm = document.getElementById('filter-form');
        this.estudanteBusca = document.getElementById('estudante-busca');
        this.limparBuscaBtn = document.getElementById('limpar-busca');
        this.toggleVisualizacaoBtn = document.getElementById('toggle-visualizacao');
        this.tabelaView = document.getElementById('tabela-view');
        this.cardsView = document.getElementById('cards-view');
        this.exportarBtn = document.getElementById('exportar-dados');
    }

    init() {
        this.setupTooltips();
        this.setupMesSelectors();
        this.setupBuscaEstudante();
        this.setupToggleVisualizacao();
        this.setupExport();
        this.setupFilterForm();
        this.setupPaginationLinks();
        this.setupRemoveFilters();
        this.highlightActiveMonth();
        this.addRowClickHandlers();
        this.addDebugInfo();
    }

    setupTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"]')
        );
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                trigger: 'hover'
            });
        });
    }

    setupMesSelectors() {
        // Seletor principal
        if (this.mesSelector) {
            this.mesSelector.addEventListener('change', (e) => {
                this.updateUrlWithParam('mes', e.target.value);
            });
        }

        // Seletor secundário
        if (this.mesSelector2 && this.hiddenMes) {
            this.mesSelector2.addEventListener('change', (e) => {
                this.hiddenMes.value = e.target.value;
            });
        }
    }

    setupBuscaEstudante() {
        if (this.estudanteBusca && this.limparBuscaBtn) {
            let searchTimeout;

            // Busca com debounce
            this.estudanteBusca.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    const valor = e.target.value.trim();
                    if (valor) {
                        this.updateUrlWithParam('estudante', valor);
                    } else {
                        this.removeUrlParam('estudante');
                    }
                }, 500);
            });

            // Limpar busca
            this.limparBuscaBtn.addEventListener('click', () => {
                this.estudanteBusca.value = '';
                this.removeUrlParam('estudante');
            });
        }
    }

    setupToggleVisualizacao() {
        if (this.toggleVisualizacaoBtn && this.tabelaView && this.cardsView) {
            this.toggleVisualizacaoBtn.addEventListener('click', () => {
                const isTabelaVisible = !this.tabelaView.classList.contains('d-none');

                if (isTabelaVisible) {
                    // Mostrar cards
                    this.tabelaView.classList.add('d-none');
                    this.cardsView.classList.remove('d-none');
                    this.toggleVisualizacaoBtn.innerHTML = '<i class="fas fa-table me-1"></i> Tabela';
                    localStorage.setItem('alertas-view-mode', 'cards');
                } else {
                    // Mostrar tabela
                    this.tabelaView.classList.remove('d-none');
                    this.cardsView.classList.add('d-none');
                    this.toggleVisualizacaoBtn.innerHTML = '<i class="fas fa-th-large me-1"></i> Cards';
                    localStorage.setItem('alertas-view-mode', 'tabela');
                }
            });

            // Restaurar preferência do usuário
            const viewMode = localStorage.getItem('alertas-view-mode') || 'tabela';
            if (viewMode === 'cards') {
                this.toggleVisualizacaoBtn.click();
            }
        }
    }

    setupExport() {
        if (this.exportarBtn) {
            this.exportarBtn.addEventListener('click', () => {
                const exportModal = new bootstrap.Modal(document.getElementById('exportModal'));
                exportModal.show();
            });

            // Configurar botão de confirmação de exportação
            const confirmExportBtn = document.getElementById('confirmExport');
            if (confirmExportBtn) {
                confirmExportBtn.addEventListener('click', () => {
                    const format = document.querySelector('input[name="exportFormat"]:checked').value;
                    const period = document.getElementById('exportPeriod').value;

                    this.exportData(format, period);
                });
            }
        }
    }

    exportData(format, period) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) loadingOverlay.classList.add('active');

        // Construir URL de exportação
        const url = new URL(window.location.href);
        url.pathname = url.pathname.replace('dashboard', 'export');
        url.searchParams.set('format', format);
        url.searchParams.set('period', period);

        // Criar link temporário para download
        const link = document.createElement('a');
        link.href = url.toString();
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Esconder loading após delay
        setTimeout(() => {
            if (loadingOverlay) loadingOverlay.classList.remove('active');

            // Mostrar toast de sucesso
            this.showToast('Exportação iniciada. O arquivo será baixado em instantes.', 'success');
        }, 1000);
    }

    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || (() => {
            const container = document.createElement('div');
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
            return container;
        })();

        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();

        // Remover após esconder
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    setupFilterForm() {
        if (this.filterForm) {
            this.filterForm.addEventListener('submit', (e) => {
                // Garantir que o mês oculto está atualizado
                if (this.mesSelector2 && this.hiddenMes) {
                    this.hiddenMes.value = this.mesSelector2.value;
                }
            });
        }
    }

    updateUrlWithParam(param, value) {
        const url = new URL(window.location.href);
        url.searchParams.set(param, value);
        url.searchParams.delete('page'); // Resetar para primeira página
        window.location.href = url.toString();
    }

    removeUrlParam(param) {
        const url = new URL(window.location.href);
        url.searchParams.delete(param);
        url.searchParams.delete('page'); // Resetar para primeira página
        window.location.href = url.toString();
    }

    setupPaginationLinks() {
        const urlParams = new URLSearchParams(window.location.search);
        const currentMonth = urlParams.get('mes');
        const currentTurma = urlParams.get('turma');
        const currentTipo = urlParams.get('tipo');
        const currentEstudante = urlParams.get('estudante');
        const currentStatus = urlParams.get('status');

        const paginationLinks = document.querySelectorAll('.pagination a');
        paginationLinks.forEach(link => {
            const url = new URL(link.href);

            if (currentMonth) url.searchParams.set('mes', currentMonth);
            if (currentTurma) url.searchParams.set('turma', currentTurma);
            if (currentTipo) url.searchParams.set('tipo', currentTipo);
            if (currentEstudante) url.searchParams.set('estudante', currentEstudante);
            if (currentStatus) url.searchParams.set('status', currentStatus);

            link.href = url.toString();
        });
    }

    setupRemoveFilters() {
        document.querySelectorAll('.remove-filter').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                window.location.href = this.href;
            });
        });
    }

    highlightActiveMonth() {
        const urlParams = new URLSearchParams(window.location.search);
        const currentMonth = urlParams.get('mes');

        if (currentMonth) {
            document.querySelectorAll('.month-selector option').forEach(option => {
                option.classList.toggle('month-active', option.value === currentMonth);
            });
        }
    }

    addRowClickHandlers() {
        document.querySelectorAll('.alerta-row').forEach(row => {
            row.addEventListener('click', (e) => {
                // Não fazer nada se clicou em um botão ou link
                if (e.target.closest('a') || e.target.closest('button')) {
                    return;
                }

                // Navegar para o perfil do estudante
                const estudanteLink = row.querySelector('a[href*="estudante_detail"]');
                if (estudanteLink) {
                    window.location.href = estudanteLink.href;
                }
            });
        });
    }

    addDebugInfo() {
        console.log('=== ALERTAS DASHBOARD ===');
        console.log('Versão:', '1.0.0');
        console.log('Elementos inicializados:', {
            mesSelector: !!this.mesSelector,
            filterForm: !!this.filterForm,
            estudanteBusca: !!this.estudanteBusca
        });
        console.log('========================');
    }
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar dashboard
    window.alertasDashboard = new AlertasDashboard();

    // Configurar confirmações
    const recalcularBtn = document.getElementById('recalcular-btn');
    if (recalcularBtn) {
        recalcularBtn.addEventListener('click', function(e) {
            if (!confirm('Tem certeza que deseja recalcular os alertas para este mês?\n\nEsta ação irá:\n- Limpar alertas existentes\n- Recalcular baseado nas configurações atuais\n- Pode levar alguns segundos')) {
                e.preventDefault();
            }
        });
    }

    console.log('Dashboard de Alertas inicializado com sucesso!');
});