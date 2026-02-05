from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from datetime import timedelta, datetime
from .models import RegistroRefeicao, ConfigRefeitorio, BloqueioAcesso
from core.models import Estudante, Servidor


def is_servidor(user):
    return hasattr(user, 'servidor')


# === KIOSK - Tela de Check-in ===
def checkin_screen(request):
    """Tela do totem de check-in (sem autenticação)"""
    configs_ativas = ConfigRefeitorio.objects.filter(ativo=True)

    context = {
        'configs_ativas': configs_ativas,
        'horario_atual': timezone.now().time(),
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

    # 1. Buscar pessoa (estudante ou servidor)
    estudante = Estudante.objects.filter(matricula_sga=barcode).first()
    servidor = Servidor.objects.filter(siape=barcode).first()

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
            'nome': pessoa.nome
        })

    # 3. Determinar tipo de refeição atual
    agora = timezone.now()
    config_atual = ConfigRefeitorio.objects.filter(
        ativo=True,
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time()
    ).first()

    if not config_atual:
        return render(request, 'refeitorio/partials/erro.html', {
            'mensagem': 'Fora do horário',
            'detalhes': 'Não há refeição disponível neste momento',
            'nome': pessoa.nome
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
            'nome': pessoa.nome
        })

    # 5. Registrar acesso
    registro = RegistroRefeicao.objects.create(
        **{tipo_pessoa: pessoa},
        tipo_refeicao=config_atual.nome,
        codigo_barras_usado=barcode,
        ip_acesso=request.META.get('REMOTE_ADDR')
    )

    return render(request, 'refeitorio/partials/sucesso.html', {
        'nome': pessoa.nome,
        'tipo_refeicao': config_atual.get_nome_display(),
        'horario': agora.strftime('%H:%M')
    })


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
    """Relatório por período"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if data_inicio and data_fim:
        registros = RegistroRefeicao.objects.filter(
            data_hora__date__gte=data_inicio,
            data_hora__date__lte=data_fim
        ).select_related('estudante', 'servidor')

        # Estatísticas
        total = registros.count()
        por_dia = registros.extra(
            select={'dia': 'DATE(data_hora)'}
        ).values('dia').annotate(total=Count('id')).order_by('dia')

        context = {
            'registros': registros,
            'total': total,
            'por_dia': por_dia,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }
    else:
        context = {}

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