# pedagogico/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Disciplina, ConselhoClasse, FichaAluno, InformacaoEstudanteConselho
from .forms import DisciplinaForm, ConselhoClasseForm, InformacaoEstudanteConselhoForm
from core.models import Estudante, Turma


# ========== DISCIPLINAS ==========

@login_required
def disciplina_list(request):
    """Lista disciplinas"""
    disciplinas = Disciplina.objects.all()

    curso = request.GET.get('curso')
    if curso:
        disciplinas = disciplinas.filter(curso_id=curso)

    context = {'disciplinas': disciplinas}
    return render(request, 'pedagogico/disciplina_list.html', context)


@login_required
def disciplina_create(request):
    """Criar disciplina"""
    if request.method == 'POST':
        form = DisciplinaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disciplina criada com sucesso!')
            return redirect('pedagogico:disciplina_list')
    else:
        form = DisciplinaForm()

    return render(request, 'pedagogico/disciplina_form.html', {'form': form})


# ========== CONSELHO DE CLASSE ==========

@login_required
def conselho_list(request):
    """Lista conselhos de classe"""
    conselhos = ConselhoClasse.objects.all()

    turma = request.GET.get('turma')
    periodo = request.GET.get('periodo')

    if turma:
        conselhos = conselhos.filter(turma_id=turma)
    if periodo:
        conselhos = conselhos.filter(periodo=periodo)

    context = {'conselhos': conselhos}
    return render(request, 'pedagogico/conselho_list.html', context)


@login_required
def conselho_create(request):
    """Criar conselho de classe"""
    if request.method == 'POST':
        form = ConselhoClasseForm(request.POST)
        if form.is_valid():
            conselho = form.save()
            messages.success(request, 'Conselho de Classe criado com sucesso!')
            return redirect('pedagogico:conselho_detail', pk=conselho.pk)
    else:
        form = ConselhoClasseForm()

    return render(request, 'pedagogico/conselho_form.html', {'form': form})


@login_required
def conselho_detail(request, pk):
    """Detalhes do conselho de classe"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    informacoes_estudantes = conselho.informacoes_estudantes.all()

    context = {
        'conselho': conselho,
        'informacoes_estudantes': informacoes_estudantes,
    }
    return render(request, 'pedagogico/conselho_detail.html', context)


@login_required
def conselho_estudante_edit(request, conselho_pk, estudante_id):
    """Editar informações do estudante no conselho"""
    conselho = get_object_or_404(ConselhoClasse, pk=conselho_pk)
    estudante = get_object_or_404(Estudante, id=estudante_id)

    try:
        info_estudante = InformacaoEstudanteConselho.objects.get(
            conselho=conselho,
            estudante=estudante
        )
    except InformacaoEstudanteConselho.DoesNotExist:
        info_estudante = InformacaoEstudanteConselho(
            conselho=conselho,
            estudante=estudante
        )

    if request.method == 'POST':
        form = InformacaoEstudanteConselhoForm(request.POST, instance=info_estudante)
        if form.is_valid():
            form.save()
            messages.success(request, 'Informações salvas com sucesso!')
            return redirect('pedagogico:conselho_detail', pk=conselho_pk)
    else:
        form = InformacaoEstudanteConselhoForm(instance=info_estudante)

    context = {
        'form': form,
        'conselho': conselho,
        'estudante': estudante,
    }
    return render(request, 'pedagogico/conselho_estudante_form.html', context)


# ========== FICHA DO ALUNO ==========

@login_required
def ficha_aluno(request, matricula):
    """Dashboard completo do estudante - Ficha do Aluno"""
    estudante = get_object_or_404(Estudante, matricula_sga=matricula)

    # Verificar permissão
    servidor = request.user.servidor
    pode_visualizar = (
            request.user.is_superuser or
            servidor.pode_visualizar_ficha_aluno or
            servidor.coordenacao in ['CDPD', 'CC', 'CGEN', 'DREP', 'DG']
    )

    if not pode_visualizar:
        messages.error(request, 'Você não tem permissão para visualizar esta ficha.')
        return redirect('core:estudante_list')

    # Agregando informações
    from atendimentos.models import Atendimento

    ocorrencias = estudante.ocorrencias.all()
    atendimentos = Atendimento.objects.filter(
        estudantes=estudante,
        publicar_ficha_aluno=True
    )

    # Conselhos de classe
    conselhos_info = InformacaoEstudanteConselho.objects.filter(
        estudante=estudante
    ).select_related('conselho').order_by('-conselho__data_realizacao')

    # Estatísticas
    total_ocorrencias = ocorrencias.count()
    total_atendimentos = atendimentos.count()

    context = {
        'estudante': estudante,
        'ocorrencias': ocorrencias[:10],  # Últimas 10
        'atendimentos': atendimentos[:10],  # Últimos 10
        'conselhos_info': conselhos_info,
        'total_ocorrencias': total_ocorrencias,
        'total_atendimentos': total_atendimentos,
    }
    return render(request, 'pedagogico/ficha_aluno.html', context)