from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from core.views import is_servidor
from core.decorators import coordenacao_required
from .models import Projeto, ParticipacaoServidor, ParticipacaoEstudante, AlertaRelatorio
from .forms import (
    ProjetoForm, ParticipacaoServidorForm, ParticipacaoEstudanteForm,
    FiltroProjetoForm, RelatorioEntregueForm, DefinirProximoRelatorioForm,
    ParticipacaoServidorFormSet, ParticipacaoEstudanteFormSet
)


def is_coord_pesquisa_extensao(user):
    """Verifica se é coordenador de pesquisa/extensão"""
    return (
            user.is_superuser or
            (hasattr(user, 'servidor') and user.servidor.coordenacao in ['CGEN', 'DG'])
    )


@login_required
def projeto_list(request):
    """Lista projetos baseado em permissões do servidor"""
    if not hasattr(request.user, 'servidor'):
        messages.error(request, 'Acesso restrito a servidores.')
        return redirect('core:home')

    servidor = request.user.servidor
    is_coord = is_coord_pesquisa_extensao(request.user)

    # Filtrar projetos baseado em permissão
    if is_coord:
        # Coord. pesquisa/extensão: vê todos
        projetos = Projeto.objects.all()
    else:
        # Outros: vê apenas onde está como coordenador ou participante
        projetos = Projeto.objects.filter(
            Q(coordenador=servidor) |
            Q(servidores_participantes=servidor)
        ).distinct()

    # Aplicar filtros
    filtro_form = FiltroProjetoForm(request.GET)
    if filtro_form.is_valid():
        if filtro_form.cleaned_data.get('situacao'):
            projetos = projetos.filter(situacao=filtro_form.cleaned_data['situacao'])
        if filtro_form.cleaned_data.get('tipo'):
            projetos = projetos.filter(tipo=filtro_form.cleaned_data['tipo'])
        if filtro_form.cleaned_data.get('coordenador'):
            projetos = projetos.filter(coordenador=filtro_form.cleaned_data['coordenador'])
        if filtro_form.cleaned_data.get('ano'):
            ano = filtro_form.cleaned_data['ano']
            projetos = projetos.filter(
                Q(data_inicio__year=ano) | Q(data_final__year=ano)
            )
        if filtro_form.cleaned_data.get('relatorio_atrasado'):
            hoje = timezone.now().date()
            projetos = projetos.filter(
                situacao='ATIVO',
                proximo_relatorio__lt=hoje
            )

    # Busca textual
    busca = request.GET.get('q')
    if busca:
        projetos = projetos.filter(
            Q(titulo__icontains=busca) |
            Q(numero_processo__icontains=busca) |
            Q(tema__icontains=busca) |
            Q(area__icontains=busca)
        )

    # Paginação
    projetos = projetos.select_related('coordenador').order_by('-data_inicio')
    paginator = Paginator(projetos, 20)
    page = request.GET.get('page')
    projetos_page = paginator.get_page(page)

    # Adicionar atributo para permissão de edição
    for projeto in projetos_page:
        projeto.user_can_edit = projeto.pode_editar(servidor) or is_coord

    # Estatísticas
    estatisticas = {
        'total': projetos.count(),
        'ativos': projetos.filter(situacao='ATIVO').count(),
        'com_atraso': projetos.filter(
            situacao='ATIVO',
            proximo_relatorio__lt=timezone.now().date()
        ).count()
    }

    context = {
        'projetos': projetos_page,
        'filtro_form': filtro_form,
        'busca': busca,
        'estatisticas': estatisticas,
        'is_coord_pesquisa_extensao': is_coord,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': ''}
        ]
    }

    return render(request, 'projetos/projeto_list.html', context)


@login_required
@coordenacao_required(['CGEN', 'DG'])
def projeto_create(request):
    """Criar projeto - apenas coord. pesquisa/extensão"""
    servidor = request.user.servidor

    if request.method == 'POST':
        form = ProjetoForm(request.POST, servidor=servidor)
        if form.is_valid():
            projeto = form.save()
            messages.success(request, f'Projeto "{projeto.titulo}" criado com sucesso!')
            return redirect('projetos:projeto_detail', pk=projeto.pk)
    else:
        form = ProjetoForm(servidor=servidor)

    context = {
        'form': form,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': 'Novo Projeto', 'url': ''}
        ]
    }

    return render(request, 'projetos/projeto_form.html', context)


@login_required
def projeto_detail(request, pk):
    """Detalhes do projeto"""
    projeto = get_object_or_404(
        Projeto.objects.select_related('coordenador', 'criado_por')
        .prefetch_related('servidores_participantes', 'estudantes'),
        pk=pk
    )

    servidor = request.user.servidor

    # Verificar permissão de visualização
    if not projeto.pode_visualizar(servidor) and not is_coord_pesquisa_extensao(request.user):
        messages.error(request, 'Você não tem permissão para visualizar este projeto.')
        return redirect('projetos:projeto_list')

    # Participações
    participacoes_servidor = ParticipacaoServidor.objects.filter(
        projeto=projeto
    ).select_related('servidor').order_by('-semestre', 'servidor__nome')

    participacoes_estudante = ParticipacaoEstudante.objects.filter(
        projeto=projeto
    ).select_related('estudante').order_by('-data_inicio')

    # Verificar alertas
    alerta_relatorio = None
    if projeto.relatorio_atrasado():
        alerta_relatorio = {
            'tipo': 'danger',
            'mensagem': f'Relatório vencido em {projeto.proximo_relatorio.strftime("%d/%m/%Y")}'
        }
    elif projeto.proximo_relatorio:
        dias_faltam = (projeto.proximo_relatorio - timezone.now().date()).days
        if 0 <= dias_faltam <= 7:
            alerta_relatorio = {
                'tipo': 'warning',
                'mensagem': f'Próximo relatório em {dias_faltam} dias ({projeto.proximo_relatorio.strftime("%d/%m/%Y")})'
            }

    context = {
        'projeto': projeto,
        'participacoes_servidor': participacoes_servidor,
        'participacoes_estudante': participacoes_estudante,
        'alerta_relatorio': alerta_relatorio,
        'pode_editar': projeto.pode_editar(servidor) or is_coord_pesquisa_extensao(request.user),
        'is_coord_pesquisa_extensao': is_coord_pesquisa_extensao(request.user),
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:50], 'url': ''}
        ]
    }

    return render(request, 'projetos/projeto_detail.html', context)


@login_required
def projeto_edit(request, pk):
    """Editar projeto"""
    projeto = get_object_or_404(Projeto, pk=pk)
    servidor = request.user.servidor

    # Verificar permissão de edição
    if not projeto.pode_editar(servidor) and not is_coord_pesquisa_extensao(request.user):
        messages.error(request, 'Você não tem permissão para editar este projeto.')
        return redirect('projetos:projeto_detail', pk=pk)

    if request.method == 'POST':
        form = ProjetoForm(request.POST, instance=projeto, servidor=servidor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Projeto atualizado com sucesso!')
            return redirect('projetos:projeto_detail', pk=pk)
    else:
        form = ProjetoForm(instance=projeto, servidor=servidor)

    context = {
        'form': form,
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Editar', 'url': ''}
        ]
    }

    return render(request, 'projetos/projeto_form.html', context)


@login_required
@coordenacao_required(['CGEN', 'DG'])
def projeto_delete(request, pk):
    """Excluir projeto - apenas coord. pesquisa/extensão"""
    projeto = get_object_or_404(Projeto, pk=pk)

    if request.method == 'POST':
        titulo = projeto.titulo
        projeto.delete()
        messages.success(request, f'Projeto "{titulo}" excluído com sucesso!')
        return redirect('projetos:projeto_list')

    context = {
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Excluir', 'url': ''}
        ]
    }

    return render(request, 'projetos/projeto_confirm_delete.html', context)


@login_required
def participacao_servidor_edit(request, pk):
    """Gerenciar participações de servidores"""
    projeto = get_object_or_404(Projeto, pk=pk)
    servidor = request.user.servidor

    # Verificar permissão
    if not projeto.pode_editar(servidor) and not is_coord_pesquisa_extensao(request.user):
        messages.error(request, 'Você não tem permissão para editar participações.')
        return redirect('projetos:projeto_detail', pk=pk)

    if request.method == 'POST':
        formset = ParticipacaoServidorFormSet(request.POST, instance=projeto)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Participações de servidores atualizadas!')
            return redirect('projetos:projeto_detail', pk=pk)
    else:
        formset = ParticipacaoServidorFormSet(instance=projeto)

    context = {
        'formset': formset,
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Participações', 'url': ''}
        ]
    }

    return render(request, 'projetos/participacao_servidor_form.html', context)


@login_required
def participacao_estudante_edit(request, pk):
    """Gerenciar participações de estudantes"""
    projeto = get_object_or_404(Projeto, pk=pk)
    servidor = request.user.servidor

    # Verificar permissão
    if not projeto.pode_editar(servidor) and not is_coord_pesquisa_extensao(request.user):
        messages.error(request, 'Você não tem permissão para editar participações.')
        return redirect('projetos:projeto_detail', pk=pk)

    if request.method == 'POST':
        formset = ParticipacaoEstudanteFormSet(request.POST, instance=projeto)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Participações de estudantes atualizadas!')
            return redirect('projetos:projeto_detail', pk=pk)
    else:
        formset = ParticipacaoEstudanteFormSet(instance=projeto)

    context = {
        'formset': formset,
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Estudantes', 'url': ''}
        ]
    }

    return render(request, 'projetos/participacao_estudante_form.html', context)


@login_required
def relatorio_entregue(request, pk):
    """Marcar relatório como entregue"""
    projeto = get_object_or_404(Projeto, pk=pk)
    servidor = request.user.servidor

    # Verificar permissão (coordenador ou coord. pesquisa/extensão)
    if not projeto.pode_editar(servidor) and not is_coord_pesquisa_extensao(request.user):
        messages.error(request, 'Você não tem permissão para esta ação.')
        return redirect('projetos:projeto_detail', pk=pk)

    if request.method == 'POST':
        form = RelatorioEntregueForm(request.POST)
        if form.is_valid():
            projeto.data_ultimo_relatorio = form.cleaned_data['data_entrega']
            projeto.calcular_proximo_relatorio()
            projeto.save()

            messages.success(
                request,
                f'Relatório marcado como entregue. Próximo relatório: '
                f'{projeto.proximo_relatorio.strftime("%d/%m/%Y")}'
            )
            return redirect('projetos:projeto_detail', pk=pk)
    else:
        form = RelatorioEntregueForm(initial={'data_entrega': timezone.now().date()})

    context = {
        'form': form,
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Registrar Relatório', 'url': ''}
        ]
    }

    return render(request, 'projetos/relatorio_form.html', context)


@login_required
@coordenacao_required(['CGEN', 'DG'])
def definir_proximo_relatorio(request, pk):
    """Definir manualmente próximo relatório - apenas coord. pesquisa/extensão"""
    projeto = get_object_or_404(Projeto, pk=pk)

    if request.method == 'POST':
        form = DefinirProximoRelatorioForm(request.POST)
        if form.is_valid():
            projeto.proximo_relatorio = form.cleaned_data['proximo_relatorio']
            projeto.save()

            messages.success(
                request,
                f'Próximo relatório definido para {projeto.proximo_relatorio.strftime("%d/%m/%Y")}'
            )
            return redirect('projetos:projeto_detail', pk=pk)
    else:
        form = DefinirProximoRelatorioForm(initial={
            'proximo_relatorio': projeto.proximo_relatorio or timezone.now().date()
        })

    context = {
        'form': form,
        'projeto': projeto,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Projetos', 'url': '/projetos/'},
            {'label': projeto.titulo[:30], 'url': f'/projetos/{pk}/'},
            {'label': 'Definir Próximo Relatório', 'url': ''}
        ]
    }

    return render(request, 'projetos/definir_proximo_relatorio.html', context)


@login_required
def dashboard_projetos(request):
    """Dashboard específico para projetos"""
    if not hasattr(request.user, 'servidor'):
        return redirect('core:home')

    servidor = request.user.servidor
    is_coord = is_coord_pesquisa_extensao(request.user)

    # Estatísticas
    if is_coord:
        projetos_base = Projeto.objects.all()
    else:
        projetos_base = Projeto.objects.filter(
            Q(coordenador=servidor) | Q(servidores_participantes=servidor)
        ).distinct()

    stats = {
        'total': projetos_base.count(),
        'ativos': projetos_base.filter(situacao='ATIVO').count(),
        'finalizados': projetos_base.filter(situacao='FINALIZADO').count(),
        'pendentes': projetos_base.filter(situacao='PENDENTE').count(),
        'com_atraso': projetos_base.filter(
            situacao='ATIVO',
            proximo_relatorio__lt=timezone.now().date()
        ).count(),
    }

    # Projetos com relatório próximo (7 dias)
    projetos_alerta = projetos_base.filter(
        situacao='ATIVO',
        proximo_relatorio__lte=timezone.now().date() + timedelta(days=7),
        proximo_relatorio__gte=timezone.now().date()
    ).select_related('coordenador')

    # Projetos com atraso
    projetos_atrasados = projetos_base.filter(
        situacao='ATIVO',
        proximo_relatorio__lt=timezone.now().date()
    ).select_related('coordenador')

    context = {
        'stats': stats,
        'projetos_alerta': projetos_alerta,
        'projetos_atrasados': projetos_atrasados,
        'is_coord': is_coord,
        'breadcrumbs_list': [
            {'label': 'Dashboard', 'url': '/'},
            {'label': 'Dashboard Projetos', 'url': ''}
        ]
    }

    return render(request, 'projetos/dashboard.html', context)


@login_required
def api_horas_servidor(request):
    """API: retorna total de horas de um servidor em um semestre"""
    servidor_id = request.GET.get('servidor_id')
    semestre = request.GET.get('semestre', Projeto.get_semestre_atual())

    if not servidor_id:
        return JsonResponse({'error': 'servidor_id obrigatório'}, status=400)

    total = ParticipacaoServidor.objects.filter(
        servidor_id=servidor_id,
        semestre=semestre
    ).aggregate(total=Sum('horas_semanais'))['total'] or 0

    return JsonResponse({
        'servidor_id': servidor_id,
        'semestre': semestre,
        'total_horas': float(total),
        'horas_disponiveis': 12 - float(total)
    })