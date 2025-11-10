from django.db import models
from core.models import Servidor, Turma, Estudante, Curso
from django.utils import timezone


class Disciplina(models.Model):
    """Disciplinas do curso"""
    nome = models.CharField(max_length=200)
    codigo = models.CharField(max_length=20, unique=True)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='disciplinas')
    carga_horaria = models.IntegerField()
    ementa = models.TextField(blank=True)
    ativa = models.BooleanField(default=True)

    # Configuração de bimestres (separados por vírgula: "1,2,3,4")
    bimestres_ativos = models.CharField(
        max_length=20,
        default="1,2,3,4",
        help_text="Bimestres em que a disciplina é ofertada (ex: 1,2)"
    )

    class Meta:
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        ordering = ['nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def esta_ativa_no_bimestre(self, bimestre):
        """Verifica se disciplina está ativa no bimestre"""
        return str(bimestre) in self.bimestres_ativos.split(',')


class DisciplinaTurma(models.Model):
    """Relação entre disciplina, turma e docente"""
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='disciplinas_turma')
    docente = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='disciplinas_lecionadas',
        null=True,
        blank=True
    )
    periodo = models.CharField(max_length=20)  # "2024.1", "2024.2"

    class Meta:
        unique_together = ['disciplina', 'turma', 'periodo']
        verbose_name = 'Disciplina da Turma'
        verbose_name_plural = 'Disciplinas das Turmas'

    def __str__(self):
        docente_nome = self.docente.nome if self.docente else "Sem docente"
        return f"{self.disciplina.nome} - {self.turma.nome} - {docente_nome}"


class ConselhoClasse(models.Model):
    """Conselho de classe da turma"""
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='conselhos')
    periodo = models.CharField(max_length=20)  # "2024.1", "2024.2", "2024.3", "2024.4"
    data_realizacao = models.DateField()

    # Abertura e fechamento
    aberto = models.BooleanField(default=True)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)

    # Informações gerais da turma (preenchido por coordenação)
    perfil_turma = models.TextField(
        blank=True,
        verbose_name="Perfil da turma segundo os professores"
    )
    informacoes_gerais = models.TextField(blank=True)
    pontos_positivos = models.TextField(blank=True)
    pontos_atencao = models.TextField(blank=True)
    encaminhamentos = models.TextField(blank=True)

    # Participantes (referenciando Servidor do core)
    coordenacao_curso = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='conselhos_coordenados',
        null=True,
        blank=True
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
        related_name='conselhos_participacao',
        blank=True
    )

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='conselhos_criados',
        null=True
    )

    class Meta:
        ordering = ['-data_realizacao']
        verbose_name = 'Conselho de Classe'
        verbose_name_plural = 'Conselhos de Classe'
        unique_together = ['turma', 'periodo']

    def __str__(self):
        return f"Conselho {self.turma.nome} - {self.periodo}"

    def fechar(self):
        """Fecha o conselho para novas edições"""
        self.aberto = False
        self.data_fechamento = timezone.now()
        self.save()

    def reabrir(self):
        """Reabre o conselho"""
        self.aberto = True
        self.data_fechamento = None
        self.save()


class InformacaoEstudanteConselho(models.Model):
    """Informações individuais dos estudantes no conselho"""
    conselho = models.ForeignKey(
        ConselhoClasse,
        on_delete=models.CASCADE,
        related_name='informacoes_estudantes'
    )
    estudante = models.ForeignKey(Estudante, on_delete=models.PROTECT)

    # Informações gerais (todos os estudantes)
    observacoes_gerais = models.TextField(
        blank=True,
        verbose_name="Observações sobre o estudante"
    )

    # Informações NAPNE (apenas estudantes NAPNE)
    observacoes_napne = models.TextField(
        blank=True,
        verbose_name="Observações docentes das adaptações realizadas (NAPNE)"
    )

    # Agregação de campos antigos mantidos para compatibilidade
    frequencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    situacao_geral = models.CharField(max_length=50, blank=True)
    participacao = models.TextField(blank=True)
    relacionamento = models.TextField(blank=True)
    dificuldades = models.TextField(blank=True)
    potencialidades = models.TextField(blank=True)

    # Encaminhamentos (coordenação)
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

    @property
    def eh_napne(self):
        """Verifica se estudante tem ficha NAPNE"""
        return hasattr(self.estudante, 'ficha_napne')


class ObservacaoDocenteEstudante(models.Model):
    """Observações de cada docente sobre cada estudante"""
    informacao_estudante = models.ForeignKey(
        InformacaoEstudanteConselho,
        on_delete=models.CASCADE,
        related_name='observacoes_docentes'
    )
    docente = models.ForeignKey(Servidor, on_delete=models.PROTECT)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)

    # Observação geral (obrigatória)
    observacao = models.TextField(
        verbose_name="Observações sobre o estudante"
    )

    # Observação NAPNE (obrigatória se estudante for NAPNE)
    observacao_napne = models.TextField(
        blank=True,
        verbose_name="Observações das adaptações realizadas (NAPNE)"
    )

    # Metadados
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    preenchido = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Observação Docente do Estudante'
        verbose_name_plural = 'Observações Docentes dos Estudantes'
        unique_together = ['informacao_estudante', 'docente', 'disciplina']
        ordering = ['disciplina__nome']

    def __str__(self):
        return f"{self.docente.nome} - {self.disciplina.codigo} - {self.informacao_estudante.estudante.nome}"


class ObservacaoDocenteTurma(models.Model):
    """Observação do docente sobre o perfil da turma como um todo"""
    conselho = models.ForeignKey(
        ConselhoClasse,
        on_delete=models.CASCADE,
        related_name='observacoes_turma'
    )
    docente = models.ForeignKey(Servidor, on_delete=models.PROTECT)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)

    observacao = models.TextField(
        verbose_name="Perfil da turma segundo o professor"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Observação Docente da Turma'
        verbose_name_plural = 'Observações Docentes da Turma'
        unique_together = ['conselho', 'docente', 'disciplina']

    def __str__(self):
        return f"{self.docente.nome} - {self.disciplina.codigo} - {self.conselho}"


class FichaAluno(models.Model):
    """
    Dashboard/Ficha do estudante - agregação de informações
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