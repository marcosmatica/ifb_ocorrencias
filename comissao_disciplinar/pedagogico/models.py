from django.db import models
from core.models import Servidor, Turma, Estudante, Curso


class Disciplina(models.Model):
    """Disciplinas do curso"""
    nome = models.CharField(max_length=200)
    codigo = models.CharField(max_length=20, unique=True)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='disciplinas')
    carga_horaria = models.IntegerField()
    ementa = models.TextField(blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        ordering = ['nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class DisciplinaTurma(models.Model):
    """Relação entre disciplina, turma e docente"""
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='disciplinas_turma')
    docente = models.ForeignKey(Servidor, on_delete=models.PROTECT, related_name='disciplinas_lecionadas')
    periodo = models.CharField(max_length=20)  # "2024.1", "2024.2"

    class Meta:
        unique_together = ['disciplina', 'turma', 'periodo']
        verbose_name = 'Disciplina da Turma'
        verbose_name_plural = 'Disciplinas das Turmas'

    def __str__(self):
        return f"{self.disciplina.nome} - {self.turma.nome} - {self.periodo}"


class ConselhoClasse(models.Model):
    """Conselho de classe da turma"""
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='conselhos')
    periodo = models.CharField(max_length=20)  # "2024.1", "2024.2"
    data_realizacao = models.DateField()

    # Informações gerais da turma
    informacoes_gerais = models.TextField(blank=True)
    pontos_positivos = models.TextField(blank=True)
    pontos_atencao = models.TextField(blank=True)
    encaminhamentos = models.TextField(blank=True)

    # Participantes (referenciando Servidor do core)
    coordenacao_curso = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='conselhos_coordenados',
        null=True
    )
    coordenacao_pedagogica = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='conselhos_pedagogicos',
        null=True,
        blank=True
    )
    docentes_participantes = models.ManyToManyField(
        Servidor,
        related_name='conselhos_participacao'
    )

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_realizacao']
        verbose_name = 'Conselho de Classe'
        verbose_name_plural = 'Conselhos de Classe'
        unique_together = ['turma', 'periodo']

    def __str__(self):
        return f"Conselho {self.turma.nome} - {self.periodo}"


class InformacaoEstudanteConselho(models.Model):
    """Informações individuais dos estudantes no conselho"""
    conselho = models.ForeignKey(
        ConselhoClasse,
        on_delete=models.CASCADE,
        related_name='informacoes_estudantes'
    )
    estudante = models.ForeignKey(Estudante, on_delete=models.PROTECT)

    # Informações acadêmicas
    observacoes_gerais = models.TextField(blank=True)
    frequencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    situacao_geral = models.CharField(max_length=50, blank=True)

    # Aspectos comportamentais e socioemocionais
    participacao = models.TextField(blank=True)
    relacionamento = models.TextField(blank=True)
    dificuldades = models.TextField(blank=True)
    potencialidades = models.TextField(blank=True)

    # Encaminhamentos
    necessita_acompanhamento = models.BooleanField(default=False)
    encaminhamento_cdpd = models.BooleanField(default=False, verbose_name="Encaminhamento CDPD")
    encaminhamento_cdae = models.BooleanField(default=False, verbose_name="Encaminhamento CDAE")
    encaminhamento_napne = models.BooleanField(default=False, verbose_name="Encaminhamento NAPNE")
    observacoes_encaminhamento = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Informação do Estudante no Conselho'
        verbose_name_plural = 'Informações dos Estudantes no Conselho'
        unique_together = ['conselho', 'estudante']

    def __str__(self):
        return f"{self.estudante.nome} - {self.conselho}"


class InformacaoDisciplinaConselho(models.Model):
    """Informações da disciplina para cada estudante no conselho"""
    informacao_estudante = models.ForeignKey(
        InformacaoEstudanteConselho,
        on_delete=models.CASCADE,
        related_name='disciplinas'
    )
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    docente = models.ForeignKey(Servidor, on_delete=models.PROTECT)

    nota = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    frequencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Informação de Disciplina no Conselho'
        verbose_name_plural = 'Informações de Disciplinas no Conselho'

    def __str__(self):
        return f"{self.disciplina.nome} - {self.informacao_estudante.estudante.nome}"


class FichaAluno(models.Model):
    """
    Dashboard/Ficha do estudante - agregação de informações
    Será gerada dinamicamente agregando:
    - Ocorrências (core)
    - Atendimentos (atendimentos app)
    - Atendimentos NAPNE (napne app)
    - Conselhos de Classe (pedagogico)
    - Frequência geral
    - Notas
    """
    estudante = models.OneToOneField(
        Estudante,
        on_delete=models.CASCADE,
        related_name='ficha'
    )
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ficha do Aluno'
        verbose_name_plural = 'Fichas dos Alunos'

    def __str__(self):
        return f"Ficha - {self.estudante.nome}"