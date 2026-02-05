// Auto-atualização do dashboard a cada 30s
let updateInterval;

function atualizarEstatisticas() {
    fetch('/refeitorio/api/stats/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-hoje').textContent = data.total;
            document.getElementById('estudantes-hoje').textContent = data.estudantes;
            document.getElementById('servidores-hoje').textContent = data.servidores;

            console.log('Dashboard atualizado:', data.ultima_atualizacao);
        })
        .catch(error => console.error('Erro ao atualizar:', error));
}

// Iniciar atualização automática
document.addEventListener('DOMContentLoaded', function() {
    // Atualizar a cada 30 segundos
    updateInterval = setInterval(atualizarEstatisticas, 30000);

    // Limpar intervalo ao sair da página
    window.addEventListener('beforeunload', function() {
        clearInterval(updateInterval);
    });
});

// Função para exportar dados
function exportarDados(formato) {
    const url = new URL(window.location.href);
    url.pathname = '/refeitorio/export/';
    url.searchParams.set('format', formato);
    window.location.href = url.toString();
}