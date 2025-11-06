from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import (
    FichaEstudanteNAPNE, AtendimentoNAPNE, TipoAtendimentoNAPNE,
    StatusAtendimentoNAPNE, ObservacaoEncaminhamento
)
from .forms import FichaEstudanteNAPNEForm, AtendimentoNAPNEForm, ObservacaoEncaminhamentoForm
from core.models import Estudante

@login_required
def napne_dashboard(request):
    """Dashboard do NAPNE"""
    servidor = request.user.servidor
    
    total_fichas = FichaEstudanteNAPNE.objects.count()
    total_atendimentos = AtendimentoNAPNE.objects.count()
    atendimentos_mes = AtendimentoNAPNE.objects.filter(
        data__month=timezone.now().month
    ).count()
    
    ultimos_atendimentos = AtendimentoNAPNE.objects.select_related(
        'estudante', 'atendido_por', 'tipo_atendimento', 'status'
    ).order_by('-data')[:10]
    
    context = {
        'total_fichas': total_fichas,
        'total_atendimentos': total_atendimentos,
        'atendimentos_mes': atendimentos_mes,
        'ultimos_atendimentos': ultimos_atendimentos,
    }
    return render(request, 'napne/dashboard.html', context)


@login_required
def ficha_napne_list(request):
    """Lista fichas NAPNE"""
    fichas = FichaEstudanteNAPNE.objects.select_related(
        'estudante', 'turma', 'atendido_por'
    ).order_by('estudante__nome')
    
    # Filtros
    turma = request.GET.get('turma')
    if turma:
        fichas = fichas.filter(turma_id=turma)
    
    context = {'fichas': fichas}
    return render(request, 'napne/ficha_list.html', context)


@login_required
def ficha_napne_create(request):
    """Criar ficha NAPNE"""
    if request.method == 'POST':
        form = FichaEstudanteNAPNEForm(request.POST)
        if form.is_valid():
            ficha = form.save()
            messages.success(request, 'Ficha NAPNE criada com sucesso!')
            return redirect('napne:ficha_detail', pk=ficha.pk)
    else:
        form = FichaEstudanteNAPNEForm()
    
    return render(request, 'napne/ficha_form.html', {'form': form})


@login_required
def ficha_napne_detail(request, pk):
    """Detalhes da ficha NAPNE"""
    ficha = get_object_or_404(
        FichaEstudanteNAPNE.objects.select_related('estudante', 'turma', 'atendido_por'),
        pk=pk
    )
    atendimentos = ficha.atendimentos.select_related(
        'atendido_por', 'tipo_atendimento', 'status'
    ).order_by('-data')
    
    context = {
        'ficha': ficha,
        'atendimentos': atendimentos,
    }
    return render(request, 'napne/ficha_detail.html', context)


@login_required
def ficha_napne_edit(request, pk):
    """Editar ficha NAPNE"""
    ficha = get_object_or_404(FichaEstudanteNAPNE, pk=pk)
    
    if request.method == 'POST':
        form = FichaEstudanteNAPNEForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ficha NAPNE atualizada com sucesso!')
            return redirect('napne:ficha_detail', pk=ficha.pk)
    else:
        form = FichaEstudanteNAPNEForm(instance=ficha)
    
    context = {'form': form, 'ficha': ficha}
    return render(request, 'napne/ficha_form.html', context)


@login_required
def atendimento_napne_list(request):
    """Lista atendimentos NAPNE"""
    atendimentos = AtendimentoNAPNE.objects.select_related(
        'estudante', 'turma', 'atendido_por', 'tipo_atendimento', 'status'
    ).order_by('-data')
    
    # Filtros
    estudante = request.GET.get('estudante')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    status = request.GET.get('status')
    
    if estudante:
        atendimentos = atendimentos.filter(estudante__matricula_sga=estudante)
    if data_inicio:
        atendimentos = atendimentos.filter(data__gte=data_inicio)
    if data_fim:
        atendimentos = atendimentos.filter(data__lte=data_fim)
    if status:
        atendimentos = atendimentos.filter(status_id=status)
    
    context = {
        'atendimentos': atendimentos,
        'status_list': StatusAtendimentoNAPNE.objects.filter(ativo=True),
    }
    return render(request, 'napne/atendimento_list.html', context)


@login_required
def atendimento_napne_create(request):
    """Criar atendimento NAPNE"""
    if request.method == 'POST':
        form = AtendimentoNAPNEForm(request.POST, servidor=request.user.servidor)
        if form.is_valid():
            atendimento = form.save(commit=False)
            atendimento.atendido_por = request.user.servidor
            atendimento.save()
            form.save_m2m()
            
            messages.success(request, 'Atendimento NAPNE registrado com sucesso!')
            return redirect('napne:atendimento_detail', pk=atendimento.pk)
    else:
        form = AtendimentoNAPNEForm(servidor=request.user.servidor)
    
    return render(request, 'napne/atendimento_form.html', {'form': form})


@login_required
def atendimento_napne_detail(request, pk):
    """Detalhes do atendimento NAPNE"""
    atendimento = get_object_or_404(
        AtendimentoNAPNE.objects.select_related(
            'estudante', 'turma', 'atendido_por', 'tipo_atendimento', 'status', 'laudo_previo'
        ).prefetch_related('necessidades_especificas', 'observacoes_encaminhamento'),
        pk=pk
    )
    
    context = {'atendimento': atendimento}
    return render(request, 'napne/atendimento_detail.html', context)


@login_required
def atendimento_napne_edit(request, pk):
    """Editar atendimento NAPNE"""
    atendimento = get_object_or_404(AtendimentoNAPNE, pk=pk)
    
    if request.method == 'POST':
        form = AtendimentoNAPNEForm(request.POST, instance=atendimento, servidor=request.user.servidor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Atendimento NAPNE atualizado com sucesso!')
            return redirect('napne:atendimento_detail', pk=atendimento.pk)
    else:
        form = AtendimentoNAPNEForm(instance=atendimento, servidor=request.user.servidor)
    
    context = {'form': form, 'atendimento': atendimento}
    return render(request, 'napne/atendimento_form.html', context)


@login_required
def adicionar_encaminhamento(request, atendimento_pk):
    """Adicionar observação de encaminhamento"""
    atendimento = get_object_or_404(AtendimentoNAPNE, pk=atendimento_pk)
    
    if request.method == 'POST':
        form = ObservacaoEncaminhamentoForm(request.POST)
        if form.is_valid():
            obs = form.save(commit=False)
            obs.atendimento = atendimento
            obs.save()
            messages.success(request, 'Encaminhamento adicionado com sucesso!')
            return redirect('napne:atendimento_detail', pk=atendimento.pk)
    else:
        form = ObservacaoEncaminhamentoForm()
    
    context = {'form': form, 'atendimento': atendimento}
    return render(request, 'napne/encaminhamento_form.html', context)


# API para busca de estudantes
@login_required
def api_buscar_estudantes_napne(request):
    """API para buscar estudantes para o NAPNE"""
    turma_id = request.GET.get('turma_id')
    busca = request.GET.get('busca', '').strip()
    
    estudantes = Estudante.objects.filter(situacao='ATIVO')
    
    if turma_id:
        estudantes = estudantes.filter(turma_id=turma_id)
    
    if busca:
        estudantes = estudantes.filter(
            Q(nome__icontains=busca) | Q(matricula_sga__icontains=busca)
        )
    
    estudantes = estudantes.select_related('turma', 'curso').order_by('nome')[:50]
    
    data = [{
        'id': e.id,
        'nome': e.nome,
        'matricula': e.matricula_sga,
        'turma': e.turma.nome if e.turma else '',
        'curso': e.curso.nome if e.curso else ''
    } for e in estudantes]
    
    return JsonResponse({'estudantes': data})