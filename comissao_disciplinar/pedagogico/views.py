# pedagogico/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch, Count
from django.utils import timezone
from .models import (
    Disciplina, ConselhoClasse, FichaAluno,
    InformacaoEstudanteConselho, DisciplinaTurma,
    ObservacaoDocenteEstudante, ObservacaoDocenteTurma
)
from .forms import (
    DisciplinaForm, ConselhoClasseForm,
    InformacaoEstudanteConselhoForm,
    ObservacaoDocenteEstudanteForm,
    ObservacaoDocenteTurmaForm,
    DisciplinaTurmaForm
)
from core.models import Estudante, Turma, Servidor
from core.decorators import coordenacao_required


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
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_list(request):
    """Lista conselhos de classe"""
    conselhos = ConselhoClasse.objects.select_related(
        'turma', 'coordenacao_curso'
    ).annotate(
        total_docentes=Count('docentes_participantes')
    )

    turma = request.GET.get('turma')
    periodo = request.GET.get('periodo')

    if turma:
        conselhos = conselhos.filter(turma_id=turma)
    if periodo:
        conselhos = conselhos.filter(periodo=periodo)

    turmas = Turma.objects.filter(ativa=True)

    context = {
        'conselhos': conselhos,
        'turmas': turmas
    }
    return render(request, 'pedagogico/conselho_list.html', context)


@login_required
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_create(request):
    """Criar conselho de classe"""
    if request.method == 'POST':
        form = ConselhoClasseForm(request.POST)
        if form.is_valid():
            conselho = form.save(commit=False)
            conselho.criado_por = request.user.servidor
            conselho.save()

            # Criar estrutura inicial
            _criar_estrutura_conselho(conselho)

            messages.success(request, 'Conselho de Classe criado com sucesso!')
            return redirect('pedagogico:conselho_painel', pk=conselho.pk)
    else:
        form = ConselhoClasseForm()

    return render(request, 'pedagogico/conselho_form.html', {'form': form})


def _criar_estrutura_conselho(conselho):
    """Cria estrutura inicial do conselho (estudantes e disciplinas)"""
    # Pegar bimestre do período (ex: 2024.1 -> 1)
    try:
        bimestre = int(conselho.periodo.split('.')[-1])
    except:
        bimestre = 1

    # Criar InformacaoEstudanteConselho para cada estudante
    estudantes = conselho.turma.estudantes.filter(situacao='ATIVO')
    for estudante in estudantes:
        InformacaoEstudanteConselho.objects.get_or_create(
            conselho=conselho,
            estudante=estudante
        )

    # Pegar disciplinas ativas no bimestre
    disciplinas = Disciplina.objects.filter(
        curso=conselho.turma.curso,
        ativa=True
    )

    # Filtrar por bimestre ativo
    disciplinas_bimestre = [
        d for d in disciplinas
        if d.esta_ativa_no_bimestre(bimestre)
    ]

    # Criar ou pegar DisciplinaTurma
    for disciplina in disciplinas_bimestre:
        DisciplinaTurma.objects.get_or_create(
            disciplina=disciplina,
            turma=conselho.turma,
            periodo=conselho.periodo
        )


@login_required
def conselho_painel(request, pk):
    """Painel principal do conselho (interface unificada)"""
    conselho = get_object_or_404(
        ConselhoClasse.objects.select_related('turma', 'turma__curso'),
        pk=pk
    )
    servidor = request.user.servidor

    # Verificar permissão
    eh_coordenacao = servidor.coordenacao in ['CDPD', 'CC', 'CGEN', 'DREP', 'DG']
    eh_docente_turma = DisciplinaTurma.objects.filter(
        turma=conselho.turma,
        periodo=conselho.periodo,
        docente=servidor
    ).exists()

    if not (eh_coordenacao or eh_docente_turma or request.user.is_superuser):
        messages.error(request, 'Você não tem permissão para acessar este conselho.')
        return redirect('pedagogico:conselho_list')

    # Pegar disciplinas do período
    disciplinas_turma = DisciplinaTurma.objects.filter(
        turma=conselho.turma,
        periodo=conselho.periodo
    ).select_related('disciplina', 'docente')

    # Pegar estudantes
    estudantes = conselho.turma.estudantes.filter(
        situacao='ATIVO'
    ).order_by('nome')

    # Separar NAPNE e não-NAPNE
    estudantes_napne = []
    estudantes_regulares = []

    for est in estudantes:
        if hasattr(est, 'ficha_napne'):
            estudantes_napne.append(est)
        else:
            estudantes_regulares.append(est)

    # Estatísticas de preenchimento
    total_disciplinas = disciplinas_turma.count()
    total_estudantes = len(estudantes_napne) + len(estudantes_regulares)

    # Observações de turma preenchidas
    obs_turma_preenchidas = ObservacaoDocenteTurma.objects.filter(
        conselho=conselho
    ).count()

    # Observações de estudantes NAPNE preenchidas
    obs_napne_preenchidas = ObservacaoDocenteEstudante.objects.filter(
        informacao_estudante__conselho=conselho,
        informacao_estudante__estudante__in=estudantes_napne,
        preenchido=True
    ).count()

    context = {
        'conselho': conselho,
        'disciplinas_turma': disciplinas_turma,
        'estudantes_napne': estudantes_napne,
        'estudantes_regulares': estudantes_regulares,
        'eh_coordenacao': eh_coordenacao,
        'eh_docente_turma': eh_docente_turma,
        'total_disciplinas': total_disciplinas,
        'total_estudantes': total_estudantes,
        'obs_turma_preenchidas': obs_turma_preenchidas,
        'obs_napne_preenchidas': obs_napne_preenchidas,
        'total_obs_napne_esperadas': total_disciplinas * len(estudantes_napne),
    }
    return render(request, 'pedagogico/conselho_painel.html', context)


@login_required
def conselho_docente_assumir(request, pk, disciplina_turma_id):
    """Docente assume uma disciplina"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    disciplina_turma = get_object_or_404(DisciplinaTurma, pk=disciplina_turma_id)

    # Verificar se o usuário tem perfil de servidor
    if not hasattr(request.user, 'servidor') or not request.user.servidor:
        messages.error(request, 'Você não tem um perfil de servidor válido.')
        return redirect('pedagogico:conselho_painel', pk=pk)

    servidor = request.user.servidor

    # Verificar se o conselho está aberto
    if not conselho.aberto:
        messages.error(request, 'Este conselho está fechado para edições.')
        return redirect('pedagogico:conselho_painel', pk=pk)

    # Verificar se a disciplina já foi assumida por outro docente
    if disciplina_turma.docente and disciplina_turma.docente != servidor:
        messages.error(request, f'Esta disciplina já foi assumida por {disciplina_turma.docente.nome}.')
        return redirect('pedagogico:conselho_painel', pk=pk)

    if request.method == 'POST':
        try:
            # Atualizar o docente
            disciplina_turma.docente = servidor
            disciplina_turma.save()

            # Adicionar o docente como participante do conselho
            conselho.docentes_participantes.add(servidor)

            messages.success(request, f'Você assumiu a disciplina {disciplina_turma.disciplina.nome}')
            return redirect('pedagogico:conselho_painel', pk=pk)

        except Exception as e:
            messages.error(request, f'Erro ao assumir disciplina: {str(e)}')
            return redirect('pedagogico:conselho_painel', pk=pk)

    # Se não for POST, redirecionar
    return redirect('pedagogico:conselho_painel', pk=pk)


@login_required
def conselho_docente_preencher_turma(request, pk, disciplina_turma_id):
    """Docente preenche observação sobre a turma"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    disciplina_turma = get_object_or_404(DisciplinaTurma, pk=disciplina_turma_id)
    servidor = request.user.servidor

    # Verificar se é o docente da disciplina
    if disciplina_turma.docente != servidor and not request.user.is_superuser:
        messages.error(request, 'Você não é o docente desta disciplina.')
        return redirect('pedagogico:conselho_painel', pk=pk)

    obs_turma, created = ObservacaoDocenteTurma.objects.get_or_create(
        conselho=conselho,
        docente=servidor,
        disciplina=disciplina_turma.disciplina
    )

    if request.method == 'POST':
        form = ObservacaoDocenteTurmaForm(request.POST, instance=obs_turma)
        if form.is_valid():
            form.save()
            messages.success(request, 'Observação sobre a turma salva com sucesso!')
            return redirect('pedagogico:conselho_painel', pk=pk)
    else:
        form = ObservacaoDocenteTurmaForm(instance=obs_turma)

    context = {
        'form': form,
        'conselho': conselho,
        'disciplina_turma': disciplina_turma,
    }
    return render(request, 'pedagogico/conselho_docente_turma_form.html', context)


@login_required
def conselho_docente_preencher_estudantes(request, pk, disciplina_turma_id):
    """Docente preenche observações de todos os estudantes"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    disciplina_turma = get_object_or_404(DisciplinaTurma, pk=disciplina_turma_id)
    servidor = request.user.servidor

    # Verificar permissão
    if disciplina_turma.docente != servidor and not request.user.is_superuser:
        messages.error(request, 'Você não é o docente desta disciplina.')
        return redirect('pedagogico:conselho_painel', pk=pk)

    # Pegar todos os estudantes ativos
    estudantes = conselho.turma.estudantes.filter(situacao='ATIVO').order_by('nome')

    # Preparar dados
    dados_estudantes = []
    for estudante in estudantes:
        info_estudante, _ = InformacaoEstudanteConselho.objects.get_or_create(
            conselho=conselho,
            estudante=estudante
        )

        obs_docente, _ = ObservacaoDocenteEstudante.objects.get_or_create(
            informacao_estudante=info_estudante,
            docente=servidor,
            disciplina=disciplina_turma.disciplina
        )

        eh_napne = hasattr(estudante, 'ficha_napne')

        dados_estudantes.append({
            'estudante': estudante,
            'obs_docente': obs_docente,
            'eh_napne': eh_napne,
            'necessidade': estudante.ficha_napne.necessidade_especifica if eh_napne else None
        })

    if request.method == 'POST':
        # Processar todos os estudantes
        salvos = 0
        for dado in dados_estudantes:
            obs = dado['obs_docente']
            est_id = dado['estudante'].id

            observacao = request.POST.get(f'observacao_{est_id}', '').strip()
            observacao_napne = request.POST.get(f'observacao_napne_{est_id}', '').strip()

            # Validação: observação geral é obrigatória
            if not observacao:
                continue

            # Validação: observação NAPNE obrigatória se for NAPNE
            if dado['eh_napne'] and not observacao_napne:
                continue

            obs.observacao = observacao
            obs.observacao_napne = observacao_napne
            obs.preenchido = True
            obs.save()
            salvos += 1

        if salvos > 0:
            messages.success(request, f'{salvos} observação(ões) salva(s) com sucesso!')
        else:
            messages.warning(request, 'Nenhuma observação foi salva. Verifique os campos obrigatórios.')

        return redirect('pedagogico:conselho_painel', pk=pk)

    context = {
        'conselho': conselho,
        'disciplina_turma': disciplina_turma,
        'dados_estudantes': dados_estudantes,
    }
    return render(request, 'pedagogico/conselho_docente_estudantes_form.html', context)


@login_required
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_detail(request, pk):
    """Detalhes do conselho (visão coordenação)"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    informacoes_estudantes = conselho.informacoes_estudantes.select_related(
        'estudante'
    ).prefetch_related(
        'observacoes_docentes__docente',
        'observacoes_docentes__disciplina'
    )

    context = {
        'conselho': conselho,
        'informacoes_estudantes': informacoes_estudantes,
    }
    return render(request, 'pedagogico/conselho_detail.html', context)


@login_required
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_estudante_edit(request, conselho_pk, estudante_id):
    """Coordenação edita informações agregadas do estudante"""
    conselho = get_object_or_404(ConselhoClasse, pk=conselho_pk)
    estudante = get_object_or_404(Estudante, id=estudante_id)

    info_estudante, _ = InformacaoEstudanteConselho.objects.get_or_create(
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

    # Pegar observações dos docentes
    observacoes_docentes = info_estudante.observacoes_docentes.all()

    context = {
        'form': form,
        'conselho': conselho,
        'estudante': estudante,
        'observacoes_docentes': observacoes_docentes,
    }
    return render(request, 'pedagogico/conselho_estudante_form.html', context)


@login_required
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_fechar(request, pk):
    """Fechar conselho para edições"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    conselho.fechar()
    messages.success(request, 'Conselho fechado com sucesso!')
    return redirect('pedagogico:conselho_detail', pk=pk)


@login_required
@coordenacao_required(['CDPD', 'CC', 'CGEN', 'DREP', 'DG'])
def conselho_reabrir(request, pk):
    """Reabrir conselho"""
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    conselho.reabrir()
    messages.success(request, 'Conselho reaberto com sucesso!')
    return redirect('pedagogico:conselho_detail', pk=pk)


# ========== FICHA DO ALUNO ==========

@login_required
def ficha_aluno(request, matricula):
    """Dashboard completo do estudante"""
    estudante = get_object_or_404(Estudante, matricula_sga=matricula)

    servidor = request.user.servidor
    pode_visualizar = (
            request.user.is_superuser or
            servidor.pode_visualizar_ficha_aluno or
            servidor.coordenacao in ['CDPD', 'CC', 'CGEN', 'DREP', 'DG']
    )

    if not pode_visualizar:
        messages.error(request, 'Você não tem permissão para visualizar esta ficha.')
        return redirect('core:estudante_list')

    from atendimentos.models import Atendimento
    from core.models import OcorrenciaRapida

    ocorrencias = estudante.ocorrencias.all()
    ocorrencias_rapidas = OcorrenciaRapida.objects.filter(estudantes=estudante)
    atendimentos = Atendimento.objects.filter(
        estudantes=estudante,
        publicar_ficha_aluno=True
    )

    conselhos_info = InformacaoEstudanteConselho.objects.filter(
        estudante=estudante
    ).select_related('conselho').order_by('-conselho__data_realizacao')

    total_ocorrencias = ocorrencias.count()
    total_ocorrencias_rapidas = ocorrencias_rapidas.count()
    total_atendimentos = atendimentos.count()

    context = {
        'estudante': estudante,
        'ocorrencias': ocorrencias[:10],
        'ocorrencias_rapidas': ocorrencias_rapidas[:10],
        'atendimentos': atendimentos[:10],
        'conselhos_info': conselhos_info,
        'total_ocorrencias': total_ocorrencias,
        'total_ocorrencias_rapidas': total_ocorrencias_rapidas,
        'total_atendimentos': total_atendimentos,
    }
    return render(request, 'pedagogico/ficha_aluno.html', context)