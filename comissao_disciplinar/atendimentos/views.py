# atendimentos/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Atendimento, TipoAtendimento, SituacaoAtendimento
from .forms import AtendimentoForm
from core.models import Estudante


@login_required
def atendimento_list(request):
    """Lista todos os atendimentos"""
    servidor = request.user.servidor

    # Filtrar por coordenação do servidor
    if not request.user.is_superuser:
        atendimentos = Atendimento.objects.filter(coordenacao=servidor.coordenacao)
    else:
        atendimentos = Atendimento.objects.all()

    # Filtros
    coordenacao = request.GET.get('coordenacao')
    estudante = request.GET.get('estudante')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if coordenacao:
        atendimentos = atendimentos.filter(coordenacao=coordenacao)
    if estudante:
        atendimentos = atendimentos.filter(estudantes__matricula_sga=estudante)
    if data_inicio:
        atendimentos = atendimentos.filter(data__gte=data_inicio)
    if data_fim:
        atendimentos = atendimentos.filter(data__lte=data_fim)

    context = {
        'atendimentos': atendimentos,
        #'coordenacoes': Atendimento.coordenacao.choices,
    }
    return render(request, 'atendimentos/atendimento_list.html', context)


@login_required
def atendimento_create(request):
    """Registrar novo atendimento"""
    if request.method == 'POST':
        form = AtendimentoForm(request.POST, request.FILES, servidor=request.user.servidor)
        if form.is_valid():
            atendimento = form.save()
            messages.success(request, 'Atendimento registrado com sucesso!')
            return redirect('atendimento_detail', pk=atendimento.pk)
    else:
        form = AtendimentoForm(servidor=request.user.servidor)

    return render(request, 'atendimentos/atendimento_form.html', {'form': form})


@login_required
def atendimento_detail(request, pk):
    """Detalhes do atendimento"""
    atendimento = get_object_or_404(Atendimento, pk=pk)

    # Verificar permissão
    pode_visualizar = (
            request.user.is_superuser or
            atendimento.servidor_responsavel == request.user.servidor or
            request.user.servidor in atendimento.servidores_participantes.all() or
            atendimento.coordenacao == request.user.servidor.coordenacao
    )

    if not pode_visualizar:
        messages.error(request, 'Você não tem permissão para visualizar este atendimento.')
        return redirect('atendimento_list')

    context = {'atendimento': atendimento}
    return render(request, 'atendimentos/atendimento_detail.html', context)


@login_required
def atendimentos_por_estudante(request, matricula):
    """Listar atendimentos de um estudante"""
    estudante = get_object_or_404(Estudante, matricula_sga=matricula)
    atendimentos = Atendimento.objects.filter(estudantes=estudante)

    context = {
        'estudante': estudante,
        'atendimentos': atendimentos,
    }
    return render(request, 'atendimentos/atendimentos_estudante.html', context)