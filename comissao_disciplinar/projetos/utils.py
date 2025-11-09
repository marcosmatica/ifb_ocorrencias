from django.db.models import Sum
from django.utils import timezone
from .models import ParticipacaoServidor, Projeto


def verificar_disponibilidade_horas(servidor, semestre, horas_adicionar, excluir_participacao_id=None):
    """
    Verifica se servidor tem horas disponíveis

    Args:
        servidor: Instância de Servidor
        semestre: String no formato YYYY.S
        horas_adicionar: Horas a adicionar
        excluir_participacao_id: ID da participação a excluir do cálculo (para edição)

    Returns:
        tuple: (disponivel: bool, horas_usadas: float, horas_disponiveis: float)
    """
    participacoes = ParticipacaoServidor.objects.filter(
        servidor=servidor,
        semestre=semestre
    )

    if excluir_participacao_id:
        participacoes = participacoes.exclude(id=excluir_participacao_id)

    total_usado = participacoes.aggregate(
        total=Sum('horas_semanais')
    )['total'] or 0

    horas_disponiveis = 12 - float(total_usado)
    disponivel = horas_disponiveis >= float(horas_adicionar)

    return disponivel, float(total_usado), horas_disponiveis


def gerar_relatorio_horas_servidor(servidor, semestre=None):
    """
    Gera relatório de horas de um servidor

    Returns:
        dict com informações consolidadas
    """
    if not semestre:
        semestre = Projeto.get_semestre_atual()

    participacoes = ParticipacaoServidor.objects.filter(
        servidor=servidor,
        semestre=semestre
    ).select_related('projeto')

    projetos_detalhes = []
    total_horas = 0

    for participacao in participacoes:
        projetos_detalhes.append({
            'projeto': participacao.projeto.titulo,
            'numero_processo': participacao.projeto.numero_processo,
            'horas': float(participacao.horas_semanais),
            'situacao': participacao.projeto.situacao
        })
        total_horas += float(participacao.horas_semanais)

    return {
        'servidor': servidor.nome,
        'semestre': semestre,
        'projetos': projetos_detalhes,
        'total_horas': total_horas,
        'horas_disponiveis': 12 - total_horas,
        'percentual_uso': (total_horas / 12) * 100
    }


def listar_projetos_atrasados():
    """Lista todos os projetos com relatórios atrasados"""
    hoje = timezone.now().date()

    return Projeto.objects.filter(
        situacao='ATIVO',
        proximo_relatorio__lt=hoje
    ).select_related('coordenador').order_by('proximo_relatorio')


def listar_projetos_proximos(dias=7):
    """Lista projetos com relatório próximo do vencimento"""
    hoje = timezone.now().date()
    data_limite = hoje + timezone.timedelta(days=dias)

    return Projeto.objects.filter(
        situacao='ATIVO',
        proximo_relatorio__gte=hoje,
        proximo_relatorio__lte=data_limite
    ).select_related('coordenador').order_by('proximo_relatorio')


def estatisticas_projetos():
    """Retorna estatísticas gerais dos projetos"""
    projetos = Projeto.objects.all()

    return {
        'total': projetos.count(),
        'ativos': projetos.filter(situacao='ATIVO').count(),
        'finalizados': projetos.filter(situacao='FINALIZADO').count(),
        'pendentes': projetos.filter(situacao='PENDENTE').count(),
        'pesquisa': projetos.filter(tipo='PESQUISA').count(),
        'extensao': projetos.filter(tipo='EXTENSAO').count(),
        'com_estudantes': projetos.filter(envolve_estudantes=True).count(),
        'relatorios_atrasados': listar_projetos_atrasados().count(),
    }


def validar_semestre(semestre_str):
    """
    Valida formato de semestre

    Args:
        semestre_str: String no formato YYYY.S

    Returns:
        bool: True se válido
    """
    import re
    pattern = r'^\d{4}\.[12]$'
    return bool(re.match(pattern, semestre_str))