from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from django.conf import settings
from datetime import timedelta, datetime
from .models import RegistroRefeicao, ConfigRefeitorio, BloqueioAcesso
from core.models import Estudante, Servidor
import logging

logger = logging.getLogger(__name__)

def is_servidor(user):
    return hasattr(user, 'servidor')


# === KIOSK - Tela de Check-in ===
def checkin_screen(request):
    """Tela do totem de check-in (sem autenticação)"""
    configs_ativas = ConfigRefeitorio.objects.filter(ativo=True)
    agora = timezone.now()
    agora = timezone.localtime(agora)
    # Detectar refeição atual
    config_atual = ConfigRefeitorio.objects.filter(
        ativo=True,
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time()
    ).first()

    # Estatísticas da refeição atual
    total_refeicao_atual = 0
    ultimos_acessos = []

    if config_atual:
        # Contar acessos da refeição atual (desde o início do horário hoje)
        inicio_refeicao = timezone.datetime.combine(
            agora.date(),
            config_atual.horario_inicio
        )
        inicio_refeicao = timezone.make_aware(inicio_refeicao)

        registros_refeicao = RegistroRefeicao.objects.filter(
            tipo_refeicao=config_atual.nome,
            data_hora__gte=inicio_refeicao
        )

        total_refeicao_atual = registros_refeicao.count()

        # Últimos 10 acessos
        ultimos_acessos = registros_refeicao.select_related(
            'estudante', 'servidor', 'estudante__turma'
        ).order_by('-data_hora')[:10]

    context = {
        'configs_ativas': configs_ativas,
        'horario_atual': timezone.localtime(timezone.now()).time(),
        'config_atual': config_atual,
        'total_refeicao_atual': total_refeicao_atual,
        'ultimos_acessos': ultimos_acessos,
    }

    return render(request, 'refeitorio/checkin_screen.html', context)


def validar_checkin(request):
    """Processa o código de barras e valida acesso"""
    if request.method != 'POST':
        return HttpResponse(status=405)

    barcode = request.POST.get('barcode', '').strip()

    if not barcode:
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'Código inválido',
            'detalhes': 'Aproxime novamente o cartão do leitor'
        })

    # Limpar formatação de CPF (remover . e -)
    barcode_clean = barcode.replace('.', '').replace('-', '').replace('/', '')

    # 1. Buscar pessoa (estudante ou servidor)
    # Busca por matrícula, SIAPE ou CPF
    estudante = Estudante.objects.filter(
        Q(matricula_sga=barcode) |
        Q(matricula_sga=barcode_clean) |
        Q(cpf=barcode) |
        Q(cpf=barcode_clean)
    ).first()

    servidor = Servidor.objects.filter(
        Q(siape=barcode) |
        Q(siape=barcode_clean) #|
        #Q(cpf=barcode) |
        #Q(cpf=barcode_clean)
    ).first()

    if not estudante and not servidor:
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'Não cadastrado',
            'detalhes': f'Matrícula/SIAPE {barcode} não encontrada'
        })

    pessoa = estudante or servidor
    tipo_pessoa = 'estudante' if estudante else 'servidor'

    # 2. Verificar bloqueio
    bloqueio = BloqueioAcesso.objects.filter(
        Q(**{tipo_pessoa: pessoa}),
        ativo=True
    ).first()

    if bloqueio and bloqueio.esta_ativo():
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'ACESSO BLOQUEADO',
            'detalhes': bloqueio.motivo,
            'nome': pessoa.nome,
            'foto_url': pessoa.get_foto_url_proxy() if estudante else None,
            'iniciais': pessoa.get_iniciais() if estudante else None,
        })

    agora = timezone.now()
    agora = timezone.localtime(agora)
    agora_time = timezone.localtime(agora).time()
    config_atual = ConfigRefeitorio.objects.filter(
        ativo=True,
        horario_inicio__lte=agora_time,
        horario_fim__gte=agora_time
    ).first()

    if not config_atual:
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'Fora do horário',
            'detalhes': 'Não há refeição disponível neste momento',
            'nome': pessoa.nome,
            'foto_url': pessoa.get_foto_url_proxy() if estudante else None,
            'iniciais': pessoa.get_iniciais() if estudante else None,
        })

    # 4. Verificar se já comeu (mesmo tipo de refeição)
    limite_tempo = agora - timedelta(hours=config_atual.intervalo_minimo_horas)

    ja_comeu = RegistroRefeicao.objects.filter(
        Q(**{tipo_pessoa: pessoa}),
        tipo_refeicao=config_atual.nome,
        data_hora__gte=limite_tempo
    ).exists()

    if ja_comeu:
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'Já realizou esta refeição',
            'detalhes': f'{config_atual.get_nome_display()} já registrado',
            'nome': pessoa.nome,
            'foto_url': pessoa.get_foto_url_proxy() if estudante else None,
            'iniciais': pessoa.get_iniciais() if estudante else None,
        })

    # 5. Registrar acesso
    registro = RegistroRefeicao.objects.create(
        **{tipo_pessoa: pessoa},
        tipo_refeicao=config_atual.nome,
        codigo_barras_usado=barcode,
        ip_acesso=request.META.get('REMOTE_ADDR')
    )

    # Contexto para sucesso
    context = {
        'nome': pessoa.nome,
        'tipo_refeicao': config_atual.get_nome_display(),
        'horario': agora.strftime('%H:%M'),
        'is_estudante': bool(estudante),
        'is_servidor': bool(servidor),
    }

    # Dados específicos de estudante
    if estudante:
        context.update({
            'foto_url': estudante.get_foto_url_proxy(),
            'iniciais': estudante.get_iniciais(),
            'matricula': estudante.matricula_sga,
            'turma': estudante.turma.nome if estudante.turma else 'Sem turma',
            'curso': estudante.turma.curso.nome if estudante.turma else '',
        })

    # Dados específicos de servidor
    if servidor:
        context.update({
            'siape': servidor.siape,
            'cargo': servidor.cargo if hasattr(servidor, 'cargo') else 'Servidor',
        })

    return render(request, 'refeitorio/partials/sucesso.html', context)


# === DASHBOARD ADMINISTRATIVO ===
@login_required
@user_passes_test(is_servidor)
def dashboard(request):
    """Dashboard do refeitório"""
    hoje = timezone.now().date()

    # Estatísticas do dia
    refeicoes_hoje = RegistroRefeicao.objects.filter(data_hora__date=hoje)
    total_hoje = refeicoes_hoje.count()
    estudantes_hoje = refeicoes_hoje.filter(estudante__isnull=False).count()
    servidores_hoje = refeicoes_hoje.filter(servidor__isnull=False).count()

    # Por tipo de refeição
    por_tipo = refeicoes_hoje.values('tipo_refeicao').annotate(
        total=Count('id')
    ).order_by('-total')

    # Últimos registros
    ultimos_registros = refeicoes_hoje.select_related(
        'estudante', 'servidor'
    ).order_by('-data_hora')[:20]

    # Configurações ativas
    configs = ConfigRefeitorio.objects.filter(ativo=True)

    context = {
        'total_hoje': total_hoje,
        'estudantes_hoje': estudantes_hoje,
        'servidores_hoje': servidores_hoje,
        'por_tipo': por_tipo,
        'ultimos_registros': ultimos_registros,
        'configs': configs,
    }

    return render(request, 'refeitorio/dashboard.html', context)


@login_required
@user_passes_test(is_servidor)
def relatorio_periodo(request):
    """Relatório por período com filtros"""
    from core.models import Turma

    # Capturar filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    tipo_refeicao = request.GET.get('tipo_refeicao')
    turma_id = request.GET.get('turma')
    tipo_pessoa = request.GET.get('tipo_pessoa')  # estudante, servidor, todos

    # Opções para os filtros
    tipos_refeicao = ConfigRefeitorio.TIPO_REFEICAO_CHOICES
    turmas = Turma.objects.all().order_by('nome')

    context = {
        'tipos_refeicao': tipos_refeicao,
        'turmas': turmas,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'tipo_refeicao': tipo_refeicao,
            'turma': turma_id,
            'tipo_pessoa': tipo_pessoa or 'todos',
        }
    }

    if data_inicio and data_fim:
        # Base query
        registros = RegistroRefeicao.objects.filter(
            data_hora__date__gte=data_inicio,
            data_hora__date__lte=data_fim
        ).select_related('estudante', 'servidor', 'estudante__turma', 'estudante__turma__curso')

        # Aplicar filtros adicionais
        if tipo_refeicao:
            registros = registros.filter(tipo_refeicao=tipo_refeicao)

        if turma_id:
            registros = registros.filter(estudante__turma_id=turma_id)

        if tipo_pessoa == 'estudante':
            registros = registros.filter(estudante__isnull=False)
        elif tipo_pessoa == 'servidor':
            registros = registros.filter(servidor__isnull=False)

        # Ordenar
        registros = registros.order_by('-data_hora')

        # Estatísticas gerais
        total = registros.count()
        total_estudantes = registros.filter(estudante__isnull=False).count()
        total_servidores = registros.filter(servidor__isnull=False).count()

        # Por dia
        por_dia = registros.values('data_hora__date').annotate(
            total=Count('id'),
            estudantes=Count('id', filter=Q(estudante__isnull=False)),
            servidores=Count('id', filter=Q(servidor__isnull=False))
        ).order_by('data_hora__date')

        # Por tipo de refeição
        por_tipo = registros.values('tipo_refeicao').annotate(
            total=Count('id'),
            estudantes=Count('id', filter=Q(estudante__isnull=False)),
            servidores=Count('id', filter=Q(servidor__isnull=False))
        ).order_by('-total')

        # Por turma (se for filtro de estudantes)
        por_turma = None
        if tipo_pessoa != 'servidor':
            por_turma = registros.filter(
                estudante__isnull=False
            ).values(
                'estudante__turma__nome'
            ).annotate(
                total=Count('id')
            ).order_by('-total')[:10]

        # Top 10 usuários
        top_estudantes = registros.filter(
            estudante__isnull=False
        ).values(
            'estudante__nome',
            'estudante__matricula_sga',
            'estudante__turma__nome'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]

        top_servidores = registros.filter(
            servidor__isnull=False
        ).values(
            'servidor__nome',
            'servidor__siape'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]

        # Calcular média diária
        num_dias = (datetime.strptime(data_fim, '%Y-%m-%d').date() -
                   datetime.strptime(data_inicio, '%Y-%m-%d').date()).days + 1
        media_diaria = total / num_dias if num_dias > 0 else 0

        context.update({
            'registros': registros[:100],  # Limitar para performance na tabela
            'total_registros': total,
            'total': total,
            'total_estudantes': total_estudantes,
            'total_servidores': total_servidores,
            'por_dia': por_dia,
            'por_tipo': por_tipo,
            'por_turma': por_turma,
            'top_estudantes': top_estudantes,
            'top_servidores': top_servidores,
            'num_dias': num_dias,
            'media_diaria': round(media_diaria, 1),
        })

    return render(request, 'refeitorio/relatorio.html', context)


@login_required
@user_passes_test(is_servidor)
def gerenciar_bloqueios(request):
    """Gerenciar bloqueios de acesso"""
    bloqueios = BloqueioAcesso.objects.select_related(
        'estudante', 'servidor', 'criado_por'
    ).order_by('-criado_em')

    context = {
        'bloqueios': bloqueios,
    }

    return render(request, 'refeitorio/bloqueios.html', context)


# === API para atualização em tempo real ===
@login_required
def api_estatisticas_hoje(request):
    """Retorna estatísticas do dia em JSON"""
    hoje = timezone.now().date()
    refeicoes = RegistroRefeicao.objects.filter(data_hora__date=hoje)

    data = {
        'total': refeicoes.count(),
        'estudantes': refeicoes.filter(estudante__isnull=False).count(),
        'servidores': refeicoes.filter(servidor__isnull=False).count(),
        'ultima_atualizacao': timezone.now().strftime('%H:%M:%S')
    }

    return JsonResponse(data)


def api_ultimos_acessos_kiosk(request):
    """API pública para atualização dos últimos acessos no kiosk"""
    agora = timezone.now()
    agora = timezone.localtime(agora)
    # Detectar refeição atual
    config_atual = ConfigRefeitorio.objects.filter(
        ativo=True,
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time()
    ).first()

    if not config_atual:
        return render(request, 'refeitorio/partials/ultimos_acessos.html', {
            'ultimos_acessos': [],
            'total_refeicao_atual': 0,
            'config_atual': None,
        })

    # Contar acessos da refeição atual
    inicio_refeicao = timezone.datetime.combine(
        agora.date(),
        config_atual.horario_inicio
    )
    inicio_refeicao = timezone.make_aware(inicio_refeicao)

    registros_refeicao = RegistroRefeicao.objects.filter(
        tipo_refeicao=config_atual.nome,
        data_hora__gte=inicio_refeicao
    )

    total_refeicao_atual = registros_refeicao.count()

    # Últimos 10 acessos
    ultimos_acessos = registros_refeicao.select_related(
        'estudante', 'servidor', 'estudante__turma'
    ).order_by('-data_hora')[:10]

    return render(request, 'refeitorio/partials/ultimos_acessos.html', {
        'ultimos_acessos': ultimos_acessos,
        'total_refeicao_atual': total_refeicao_atual,
        'config_atual': config_atual,
    })