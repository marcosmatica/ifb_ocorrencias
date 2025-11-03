from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.query import QuerySet
from django.contrib import messages
#from wagtail.models import Page
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import *
from .forms import *
from .utils import gerar_documento_pdf, enviar_notificacao_email
from .services import ServicoNotificacao
# Adicione estas importações para o diagnóstico de e-mail
from django.core.mail import get_connection, send_mail
from django.conf import settings


def home(request):
    """Tela inicial do sistema"""
    # Verificar se o usuário está autenticado e é servidor
    is_servidor_autenticado = request.user.is_authenticated and hasattr(request.user, 'servidor')
    is_membro_comissao = is_servidor_autenticado and request.user.servidor.membro_comissao_disciplinar

    context = {
        'is_servidor_autenticado': is_servidor_autenticado,
        'is_membro_comissao': is_membro_comissao,
    }
    return render(request, 'core/home.html', context)

def is_servidor(user):
    return hasattr(user, 'servidor')


def is_comissao(user):
    return hasattr(user, 'servidor') and user.servidor.membro_comissao_disciplinar


@login_required
@user_passes_test(is_servidor)
# Atualize a view dashboard para incluir breadcrumbs
@login_required
@user_passes_test(is_servidor)
def dashboard(request):
    servidor = request.user.servidor

    # Estatísticas gerais
    total_ocorrencias = Ocorrencia.objects.count()
    ocorrencias_abertas = Ocorrencia.objects.exclude(
        status__in=['FINALIZADA', 'ARQUIVADA']
    ).count()
    minhas_ocorrencias = Ocorrencia.objects.filter(
        responsavel_registro=servidor
    ).count()

    # Ocorrências pendentes de ação
    pendentes_analise = Ocorrencia.objects.filter(status='REGISTRADA').count()
    aguardando_defesa = Ocorrencia.objects.filter(status='AGUARDANDO_DEFESA').count()

    # Ocorrências por gravidade (últimos 30 dias)
    data_limite = timezone.now().date() - timedelta(days=30)
    ocorrencias_mes = Ocorrencia.objects.filter(data__gte=data_limite)

    por_gravidade = list(ocorrencias_mes.values(
        'infracao__gravidade'
    ).annotate(total=Count('id')))

    # Tipos de infração mais comuns
    top_infracoes = list(ocorrencias_mes.values(
        'infracao__descricao'
    ).annotate(total=Count('id')).order_by('-total')[:5])

    # Últimas ocorrências
    ultimas_ocorrencias = list(Ocorrencia.objects.select_related(
        'responsavel_registro', 'curso', 'turma'
    ).prefetch_related('estudantes').order_by('-criado_em')[:10])

    # Notificações recentes
    notificacoes_recentes = list(Notificacao.objects.filter(
        usuario=request.user
    ).order_by('-criado_em')[:5])

    # Breadcrumbs
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': ''}
    ]

    context = {
        'total_ocorrencias': total_ocorrencias,
        'ocorrencias_abertas': ocorrencias_abertas,
        'minhas_ocorrencias': minhas_ocorrencias,
        'pendentes_analise': pendentes_analise,
        'aguardando_defesa': aguardando_defesa,
        'por_gravidade': por_gravidade,
        'top_infracoes': top_infracoes,
        'ultimas_ocorrencias': ultimas_ocorrencias,
        'notificacoes_recentes': notificacoes_recentes,
        'notificacoes_nao_lidas_count': Notificacao.objects.filter(
            usuario=request.user, lida=False
        ).count(),
        'breadcrumbs_list': breadcrumbs_list,
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def estudante_detail(request, matricula):
    """Detalhes completos do estudante"""
    estudante = get_object_or_404(Estudante, matricula_sga=matricula)

    # Verificar permissão para ver ficha completa
    pode_ver_ficha = (
            request.user.is_superuser or
            (hasattr(request.user, 'servidor') and
             request.user.servidor.pode_visualizar_ficha_aluno)
    )

    context = {
        'estudante': estudante,
        'pode_ver_ficha': pode_ver_ficha,
    }
    return render(request, 'core/estudante_detail.html', context)

@login_required
@user_passes_test(is_servidor)
def ocorrencia_list(request):
    servidor = request.user.servidor
    ocorrencias = Ocorrencia.objects.select_related(
        'responsavel_registro', 'curso', 'turma', 'infracao'
    ).prefetch_related('estudantes')

    # Aplicar filtros
    filtro_form = FiltroOcorrenciaForm(request.GET)
    if filtro_form.is_valid():
        if filtro_form.cleaned_data.get('data_inicio'):
            ocorrencias = ocorrencias.filter(data__gte=filtro_form.cleaned_data['data_inicio'])
        if filtro_form.cleaned_data.get('data_fim'):
            ocorrencias = ocorrencias.filter(data__lte=filtro_form.cleaned_data['data_fim'])
        if filtro_form.cleaned_data.get('status'):
            ocorrencias = ocorrencias.filter(status=filtro_form.cleaned_data['status'])
        if filtro_form.cleaned_data.get('curso'):
            ocorrencias = ocorrencias.filter(curso=filtro_form.cleaned_data['curso'])
        if filtro_form.cleaned_data.get('turma'):
            ocorrencias = ocorrencias.filter(turma=filtro_form.cleaned_data['turma'])
        if filtro_form.cleaned_data.get('gravidade'):
            ocorrencias = ocorrencias.filter(infracao__gravidade=filtro_form.cleaned_data['gravidade'])

    # Busca textual
    busca = request.GET.get('q')
    if busca:
        ocorrencias = ocorrencias.filter(
            Q(descricao__icontains=busca) |
            Q(estudantes__nome__icontains=busca) |
            Q(estudantes__matricula_sga__icontains=busca)
        ).distinct()

    # Ordenação padrão
    ocorrencias = ocorrencias.order_by('-criado_em')

    # Paginação
    paginator = Paginator(ocorrencias, 20)
    page = request.GET.get('page')
    ocorrencias_page = paginator.get_page(page)

    context = {
        'ocorrencias': ocorrencias_page,
        'filtro_form': filtro_form,
        'busca': busca,
    }

    return render(request, 'core/ocorrencia_list.html', context)


@login_required
@user_passes_test(is_servidor)
def ocorrencia_create(request):
    servidor = request.user.servidor

    if request.method == 'POST':
        form = OcorrenciaForm(request.POST, request.FILES, servidor=servidor)
        if form.is_valid():
            ocorrencia = form.save()
            ServicoNotificacao.notificar_nova_ocorrencia(ocorrencia)
            messages.success(request, 'Ocorrência registrada com sucesso!')
            return redirect('ocorrencia_detail', pk=ocorrencia.pk)
    else:
        form = OcorrenciaForm(servidor=servidor)

    return render(request, 'core/ocorrencia_form.html', {'form': form})


@login_required
@user_passes_test(is_servidor)
def ocorrencia_rapida_create(request):
    servidor = request.user.servidor

    if request.method == 'POST':
        form = OcorrenciaRapidaForm(request.POST, servidor=servidor)
        if form.is_valid():
            ocorrencia = form.save(commit=False)
            ocorrencia.responsavel_registro = servidor
            ocorrencia.curso = form.cleaned_data['turma'].curso

            # Mapear tipo rápido para descrição
            tipo_map = dict(OcorrenciaRapidaForm.TIPOS_RAPIDOS)
            ocorrencia.descricao = f"{tipo_map[form.cleaned_data['tipo_rapido']]}"

            ocorrencia.save()
            form.save_m2m()

            messages.success(request, 'Ocorrência registrada rapidamente!')
            return redirect('dashboard')
    else:
        form = OcorrenciaRapidaForm(servidor=servidor)

    return render(request, 'core/ocorrencia_rapida_form.html', {'form': form})


@login_required
def ocorrencia_detail(request, pk):
    ocorrencia = get_object_or_404(
        Ocorrencia.objects.select_related(
            'responsavel_registro', 'curso', 'turma', 'infracao', 'sancao'
        ).prefetch_related('estudantes', 'notificacoes', 'recursos', 'documentos'),
        pk=pk
    )

    # Verificar permissão
    if hasattr(request.user, 'servidor'):
        pode_editar = request.user.servidor == ocorrencia.responsavel_registro or request.user.servidor.membro_comissao_disciplinar
    else:
        pode_editar = False

    # Breadcrumbs
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/'},
        {'label': 'Ocorrências', 'url': '/ocorrencias/'},
        {'label': f'Ocorrência #{ocorrencia.id}', 'url': ''}
    ]

    context = {
        'ocorrencia': ocorrencia,
        'pode_editar': pode_editar,
        'breadcrumbs_list': breadcrumbs_list
    }

    return render(request, 'core/ocorrencia_detail.html', context)


@login_required
@user_passes_test(is_comissao)
def ocorrencia_iniciar_analise(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)
    status_anterior = ocorrencia.status

    if ocorrencia.status == 'REGISTRADA':
        ocorrencia.iniciar_analise()
        ocorrencia.save()
        ServicoNotificacao.notificar_mudanca_status(ocorrencia, status_anterior)
        messages.success(request, 'Análise iniciada!')
    else:
        messages.warning(request, 'Ocorrência não pode ser analisada neste momento.')

    return redirect('ocorrencia_detail', pk=pk)


@login_required
@user_passes_test(is_comissao)
def ocorrencia_notificar(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    if request.method == 'POST':
        form = NotificacaoForm(request.POST)
        if form.is_valid():
            notificacao = form.save(commit=False)
            notificacao.ocorrencia = ocorrencia
            notificacao.save()

            # Atualizar status da ocorrência
            if ocorrencia.status in ['REGISTRADA', 'COMISSAO_DESIGNADA']:
                ocorrencia.notificar_estudante()
                ocorrencia.save()

            # Enviar e-mail (task assíncrona)
            enviar_notificacao_email(notificacao.id)

            messages.success(request, 'Notificação enviada!')
            return redirect('ocorrencia_detail', pk=pk)
    else:
        # Pré-preencher destinatários
        estudantes = ocorrencia.estudantes.all()
        emails = [e.email for e in estudantes]
        responsaveis = [e.responsavel for e in estudantes if e.responsavel]
        emails.extend([r.email for r in responsaveis])

        form = NotificacaoForm(initial={
            'destinatarios': ', '.join(emails),
            'tipo': 'NOTIFICACAO',
        })

    return render(request, 'core/notificacao_form.html', {
        'form': form,
        'ocorrencia': ocorrencia
    })


@login_required
def ocorrencia_apresentar_defesa(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    # Verificar se é estudante envolvido ou responsável
    # (implementar lógica de autenticação específica)

    if request.method == 'POST':
        form = DefesaForm(request.POST, request.FILES)
        if form.is_valid():
            ocorrencia.defesa_texto = form.cleaned_data['defesa_texto']
            if form.cleaned_data.get('defesa_arquivo'):
                ocorrencia.defesa_arquivo = form.cleaned_data['defesa_arquivo']

            ocorrencia.registrar_defesa()
            ocorrencia.save()

            messages.success(request, 'Defesa apresentada com sucesso!')
            return redirect('ocorrencia_detail', pk=pk)
    else:
        form = DefesaForm()

    return render(request, 'core/defesa_form.html', {
        'form': form,
        'ocorrencia': ocorrencia
    })


@login_required
@user_passes_test(is_comissao)
def ocorrencia_aplicar_sancao(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    if request.method == 'POST':
        sancao_id = request.POST.get('sancao')
        detalhes = request.POST.get('sancao_detalhes')

        if sancao_id:
            ocorrencia.sancao_id = sancao_id
            ocorrencia.sancao_detalhes = detalhes
            ocorrencia.aplicar_sancao()
            ocorrencia.save()

            messages.success(request, 'Sanção aplicada!')
            return redirect('ocorrencia_detail', pk=pk)

    sancoes = Sancao.objects.all()
    return render(request, 'core/sancao_form.html', {
        'ocorrencia': ocorrencia,
        'sancoes': sancoes
    })


@login_required
@user_passes_test(is_comissao)
def comissao_create(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    if request.method == 'POST':
        form = ComissaoForm(request.POST)
        if form.is_valid():
            comissao = form.save(commit=False)
            comissao.ocorrencia = ocorrencia
            comissao.save()
            form.save_m2m()

            ocorrencia.designar_comissao()
            ocorrencia.save()

            messages.success(request, 'Comissão designada!')
            return redirect('ocorrencia_detail', pk=pk)
    else:
        form = ComissaoForm()

    return render(request, 'core/comissao_form.html', {
        'form': form,
        'ocorrencia': ocorrencia
    })


@login_required
@user_passes_test(is_servidor)
def gerar_documento(request, pk, tipo):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)
    servidor = request.user.servidor

    # Gerar documento PDF
    arquivo_pdf = gerar_documento_pdf(ocorrencia, tipo)

    # Criar um nome de arquivo válido
    nome_arquivo = f"documento_{ocorrencia.id}_{tipo}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # Salvar no banco usando ContentFile
    from django.core.files.base import ContentFile
    documento = DocumentoGerado.objects.create(
        ocorrencia=ocorrencia,
        tipo_documento=tipo,
    )

    # Salvar o conteúdo do PDF no campo arquivo
    documento.arquivo.save(nome_arquivo, ContentFile(arquivo_pdf.getvalue()))
    documento.assinaturas.add(servidor)

    messages.success(request, f'{documento.get_tipo_documento_display()} gerado com sucesso!')
    return redirect('ocorrencia_detail', pk=pk)

@login_required
def relatorio_estudante(request, matricula):
    estudante = get_object_or_404(Estudante, matricula_sga=matricula)
    ocorrencias = estudante.ocorrencias.all().select_related(
        'curso', 'turma', 'infracao'
    ).order_by('-data')

    # Estatísticas
    total_ocorrencias = ocorrencias.count()
    por_gravidade = ocorrencias.values('infracao__gravidade').annotate(total=Count('id'))

    context = {
        'estudante': estudante,
        'ocorrencias': ocorrencias,
        'total_ocorrencias': total_ocorrencias,
        'por_gravidade': por_gravidade,
    }

    return render(request, 'core/estudante_relatorio.html', context)


@login_required
def notificacoes_list(request):
    """Lista todas as notificações do usuário"""
    notificacoes = Notificacao.objects.filter(usuario=request.user)

    # Filtros
    tipo = request.GET.get('tipo')
    if tipo:
        notificacoes = notificacoes.filter(tipo=tipo)

    lida = request.GET.get('lida')
    if lida == 'true':
        notificacoes = notificacoes.filter(lida=True)
    elif lida == 'false':
        notificacoes = notificacoes.filter(lida=False)

    context = {
        'notificacoes': notificacoes,
        'tipos_notificacao': Notificacao.TIPO_CHOICES,
    }

    return render(request, 'core/notificacoes_list.html', context)


@login_required
def notificacao_marcar_lida(request, pk):
    """Marca uma notificação como lida"""
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.lida = True
    notificacao.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notificacoes_list')


@login_required
def notificacao_marcar_todas_lidas(request):
    """Marca todas as notificações como lidas"""
    Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notificacoes_list')


@login_required
def preferencias_notificacao(request):
    """Gerencia preferências de notificação"""
    try:
        preferencias = PreferenciaNotificacao.objects.get(usuario=request.user)
    except PreferenciaNotificacao.DoesNotExist:
        preferencias = PreferenciaNotificacao.objects.create(usuario=request.user)

    if request.method == 'POST':
        preferencias.receber_email_novas_ocorrencias = request.POST.get('receber_email_novas_ocorrencias') == 'on'
        preferencias.receber_email_atualizacoes = request.POST.get('receber_email_atualizacoes') == 'on'
        preferencias.receber_email_prazos = request.POST.get('receber_email_prazos') == 'on'
        preferencias.receber_notificacoes_urgentes = request.POST.get('receber_notificacoes_urgentes') == 'on'
        preferencias.save()

        messages.success(request, 'Preferências de notificação atualizadas!')
        return redirect('preferencias_notificacao')

    return render(request, 'core/preferencias_notificacao.html', {'preferencias': preferencias})


# API para notificações não lidas (usada no navbar)
@login_required
def api_notificacoes_nao_lidas(request):
    """Retorna contagem de notificações não lidas"""
    count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
    return JsonResponse({'count': count})


# API para lista rápida de notificações (navbar dropdown)
@login_required
def api_notificacoes_recentes(request):
    """Retorna notificações recentes para o dropdown"""
    notificacoes = Notificacao.objects.filter(
        usuario=request.user
    ).order_by('-criado_em')[:5]

    data = []
    for notificacao in notificacoes:
        data.append({
            'id': notificacao.id,
            'titulo': notificacao.titulo,
            'mensagem': notificacao.mensagem,
            'tipo': notificacao.tipo,
            'lida': notificacao.lida,
            'prioridade': notificacao.prioridade,
            'criado_em': notificacao.criado_em.strftime('%d/%m/%Y %H:%M'),
            'url': notificacao.ocorrencia.get_absolute_url() if notificacao.ocorrencia else '#'
        })

    return JsonResponse({'notificacoes': data})


@login_required
@user_passes_test(is_comissao)
def comissao_dashboard(request):
    """Dashboard específico para a comissão disciplinar"""
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/dashboard/'},
        {'label': 'Comissão', 'url': ''}
    ]

    # Estatísticas para a comissão
    ocorrencias_pendentes = Ocorrencia.objects.filter(status='REGISTRADA').count()
    ocorrencias_analise = Ocorrencia.objects.filter(status='EM_ANALISE').count()
    ocorrencias_julgamento = Ocorrencia.objects.filter(status='EM_JULGAMENTO').count()
    prazos_vencendo = Ocorrencia.objects.filter(
        prazo_defesa__lte=timezone.now().date() + timedelta(days=3),
        prazo_defesa__gte=timezone.now().date(),
        status='AGUARDANDO_DEFESA'
    ).count()

    context = {
        'ocorrencias_pendentes': ocorrencias_pendentes,
        'ocorrencias_analise': ocorrencias_analise,
        'ocorrencias_julgamento': ocorrencias_julgamento,
        'prazos_vencendo': prazos_vencendo,
        'breadcrumbs_list': breadcrumbs_list,
    }
    return render(request, 'core/comissao_dashboard.html', context)


@login_required
@user_passes_test(is_comissao)
def processos_list(request):
    """Lista de processos em andamento"""
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/dashboard/'},
        {'label': 'Processos', 'url': ''}
    ]

    processos = Ocorrencia.objects.filter(
        status__in=['EM_ANALISE', 'EM_JULGAMENTO', 'AGUARDANDO_DEFESA']
    ).select_related('curso', 'turma').prefetch_related('estudantes')

    context = {
        'processos': processos,
        'breadcrumbs_list': breadcrumbs_list,
    }
    return render(request, 'core/processos_list.html', context)


@login_required
@user_passes_test(is_servidor)
def relatorios_estatisticas(request):
    """Página de relatórios e estatísticas"""
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/dashboard/'},
        {'label': 'Relatórios e Estatísticas', 'url': ''}
    ]

    # Estatísticas gerais
    total_ocorrencias = Ocorrencia.objects.count()
    ocorrencias_por_mes = Ocorrencia.objects.filter(
        data__gte=timezone.now().date() - timedelta(days=365)
    ).extra({'month': "EXTRACT(month FROM data)"}).values('month').annotate(total=Count('id'))

    context = {
        'total_ocorrencias': total_ocorrencias,
        'ocorrencias_por_mes': list(ocorrencias_por_mes),
        'breadcrumbs_list': breadcrumbs_list,
    }
    return render(request, 'core/relatorios_estatisticas.html', context)


@login_required
@user_passes_test(is_servidor)
def configuracoes_sistema(request):
    """Página de configurações do sistema"""
    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/dashboard/'},
        {'label': 'Configurações', 'url': ''}
    ]

    context = {
        'breadcrumbs_list': breadcrumbs_list,
    }
    return render(request, 'core/configuracoes_sistema.html', context)


# Adicione esta view no arquivo views.py
def guia_regulamento_discente(request):
    """Página do Guia do Regulamento Discente para impressão"""
    return render(request, 'core/guia_regulamento_discente.html')


# Adicione também esta view para o perfil do usuário
@login_required
def meu_perfil(request):
    """Página do perfil do usuário"""
    # Estatísticas do usuário
    minhas_ocorrencias = 0
    notificacoes_nao_lidas = 0

    if hasattr(request.user, 'servidor'):
        minhas_ocorrencias = Ocorrencia.objects.filter(
            responsavel_registro=request.user.servidor
        ).count()

    notificacoes_nao_lidas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False
    ).count()

    breadcrumbs_list = [
        {'label': 'Dashboard', 'url': '/dashboard/'},
        {'label': 'Meu Perfil', 'url': ''}
    ]

    context = {
        'minhas_ocorrencias': minhas_ocorrencias,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
        'breadcrumbs_list': breadcrumbs_list,
    }
    return render(request, 'core/meu_perfil.html', context)


@login_required
def diagnostico_email(request):
    """Página de diagnóstico do e-mail"""
    if not request.user.is_superuser:
        messages.error(request, 'Apenas administradores podem acessar esta página.')
        return redirect('dashboard')

    config = {
        'DEBUG': settings.DEBUG,
        'EMAIL_BACKEND': settings.EMAIL_BACKEND,
        'EMAIL_HOST': settings.EMAIL_HOST,
        'EMAIL_PORT': settings.EMAIL_PORT,
        'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
        'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
    }

    # Teste de conexão
    try:
        connection = get_connection()
        connection.open()
        conexao_ok = True
        connection.close()
    except Exception as e:
        conexao_ok = False
        erro_conexao = str(e)

    context = {
        'config': config,
        'conexao_ok': conexao_ok,
        'erro_conexao': erro_conexao if not conexao_ok else None,
    }

    return render(request, 'core/diagnostico_email.html', context)


# ADICIONE ESTA VIEW PARA TESTE DE EMAIL
@login_required
def testar_email(request):
    """View para testar configuração de e-mail"""
    if not request.user.is_superuser:
        messages.error(request, 'Apenas administradores podem executar esta ação.')
        return redirect('dashboard')

    try:
        from django.core.mail import send_mail
        send_mail(
            'Teste de E-mail - Sistema Ocorrências IFB',
            'Este é um e-mail de teste do sistema de ocorrências.\n\n'
            f'Enviado em: {timezone.now().strftime("%d/%m/%Y %H:%M")}\n'
            f'Para: {request.user.email}',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        messages.success(request, f'E-mail de teste enviado com sucesso para {request.user.email}!')
    except Exception as e:
        messages.error(request, f'Erro ao enviar e-mail: {str(e)}')

    return redirect('diagnostico_email')


@login_required
@user_passes_test(is_servidor)
def api_filtrar_estudantes(request):
    """API endpoint para filtrar estudantes por turma e busca textual"""
    turma_id = request.GET.get('turma_id')
    busca = request.GET.get('busca', '').strip()

    estudantes = Estudante.objects.filter(situacao='ATIVO')

    if turma_id:
        try:
            estudantes = estudantes.filter(turma_id=int(turma_id))
        except (ValueError, TypeError):
            pass

    if busca:
        estudantes = estudantes.filter(
            Q(nome__icontains=busca) |
            Q(matricula_sga__icontains=busca)
        )

    estudantes = estudantes.select_related('turma', 'curso').order_by('nome')[:50]

    data = [{
        'id': e.id,
        'nome': e.nome,
        'matricula': e.matricula_sga,
        'turma': e.turma.nome,
        'curso': e.curso.nome
    } for e in estudantes]

    return JsonResponse({'estudantes': data})

# core/views.py - Adicione esta função

@login_required
@user_passes_test(is_servidor)
def api_filtrar_servidores(request):
    """API endpoint para filtrar servidores por nome"""
    busca = request.GET.get('busca', '').strip()

    servidores = Servidor.objects.all()

    if busca:
        servidores = servidores.filter(
            Q(nome__icontains=busca) |
            Q(email__icontains=busca)
        )

    servidores = servidores.order_by('nome')[:50]

    data = [{
        'id': s.id,
        'nome': s.nome,
        'email': s.email,
        'coordenacao': s.coordenacao,
    } for s in servidores]

    return JsonResponse({'servidores': data})