from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField
from core.models import Servidor, Estudante, Campus
from datetime import timedelta


class Projeto(models.Model):
    SITUACAO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('FINALIZADO', 'Finalizado'),
        ('PENDENTE', 'Pendente'),
    ]

    TIPO_CHOICES = [
        ('PESQUISA', 'Pesquisa'),
        ('EXTENSAO', 'Extensão'),
    ]

    # Identificação
    numero_processo = models.CharField(max_length=50, unique=True, verbose_name='Nº do Processo')
    titulo = models.CharField(max_length=300)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='EXTENSAO')

    # Datas
    data_inicio = models.DateField()
    data_final = models.DateField()

    # Classificação
    tema = models.CharField(max_length=200)
    area = models.CharField(max_length=200)

    # Coordenação
    coordenador = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='projetos_coordenados',
        verbose_name='Coordenador'
    )

    # Participantes
    servidores_participantes = models.ManyToManyField(
        Servidor,
        through='ParticipacaoServidor',
        related_name='projetos_participantes',
        blank=True
    )

    # Estudantes
    envolve_estudantes = models.BooleanField(
        default=False,
        verbose_name='Envolve alunos pesquisadores/extensionistas?'
    )
    estudantes = models.ManyToManyField(
        Estudante,
        through='ParticipacaoEstudante',
        related_name='projetos',
        blank=True
    )

    # Status
    situacao = models.CharField(max_length=15, choices=SITUACAO_CHOICES, default='ATIVO')
    observacoes = models.TextField(blank=True)

    # Relatórios
    periodicidade_relatorio = models.IntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text='Periodicidade em meses',
        verbose_name='Periodicidade do Relatório (meses)'
    )
    data_ultimo_relatorio = models.DateField(null=True, blank=True)
    proximo_relatorio = models.DateField(null=True, blank=True)

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        Servidor,
        on_delete=models.SET_NULL,
        null=True,
        related_name='projetos_criados'
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = 'Projeto de Extensão/Pesquisa'
        verbose_name_plural = 'Projetos de Extensão/Pesquisa'
        ordering = ['-data_inicio', 'titulo']
        permissions = [
            ('coordenar_projetos', 'Pode coordenar projetos (Coord. Pesquisa/Extensão)'),
        ]

    def __str__(self):
        return f"{self.numero_processo} - {self.titulo}"

    def clean(self):
        # Validar datas
        if self.data_final and self.data_inicio and self.data_final < self.data_inicio:
            raise ValidationError('Data final não pode ser anterior à data inicial.')

        # Validar se coordenador não está na lista de participantes
        if self.pk and self.servidores_participantes.filter(id=self.coordenador.id).exists():
            raise ValidationError('O coordenador não pode ser também participante.')

    def save(self, *args, **kwargs):
        # Calcular próximo relatório se data inicial definida
        if self.data_inicio and not self.proximo_relatorio:
            self.calcular_proximo_relatorio()
        super().save(*args, **kwargs)

    def calcular_proximo_relatorio(self):
        """Calcula a data do próximo relatório"""
        if self.data_ultimo_relatorio:
            base_date = self.data_ultimo_relatorio
        else:
            base_date = self.data_inicio

        self.proximo_relatorio = base_date + timedelta(days=30 * self.periodicidade_relatorio)
        return self.proximo_relatorio

    def atualizar_relatorio_entregue(self):
        """Marca relatório como entregue e calcula próximo"""
        self.data_ultimo_relatorio = timezone.now().date()
        self.calcular_proximo_relatorio()
        self.save()

    def relatorio_atrasado(self):
        """Verifica se há relatório atrasado"""
        if not self.proximo_relatorio:
            return False
        return (
                self.situacao == 'ATIVO' and
                self.proximo_relatorio < timezone.now().date()
        )

    def total_horas_projeto(self):
        """Calcula total de horas semanais do projeto"""
        total = ParticipacaoServidor.objects.filter(
            projeto=self,
            semestre=self.get_semestre_atual()
        ).aggregate(models.Sum('horas_semanais'))
        return total['horas_semanais__sum'] or 0

    @staticmethod
    def get_semestre_atual():
        """Retorna o semestre atual no formato YYYY.S"""
        hoje = timezone.now().date()
        semestre = 1 if hoje.month <= 6 else 2
        return f"{hoje.year}.{semestre}"

    def pode_editar(self, servidor):
        """Verifica se servidor pode editar o projeto"""
        # Coordenadores de pesquisa/extensão
        if servidor.coordenacao in ['CGEN', 'DG'] or servidor.user.is_superuser:
            return True
        # Coordenador do projeto
        if self.coordenador == servidor:
            return True
        return False

    def pode_visualizar(self, servidor):
        """Verifica se servidor pode visualizar o projeto"""
        if self.pode_editar(servidor):
            return True
        # Participantes
        if self.servidores_participantes.filter(id=servidor.id).exists():
            return True
        return False


class ParticipacaoServidor(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    semestre = models.CharField(
        max_length=10,
        help_text='Formato: YYYY.S (ex: 2024.1)'
    )
    horas_semanais = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0.5), MaxValueValidator(12)],
        help_text='Horas semanais dedicadas ao projeto'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['projeto', 'servidor', 'semestre']
        verbose_name = 'Participação de Servidor'
        verbose_name_plural = 'Participações de Servidores'
        ordering = ['-semestre', 'servidor__nome']

    def __str__(self):
        return f"{self.servidor.nome} - {self.projeto.titulo} ({self.semestre})"

    def clean(self):
        # Validar total de horas do servidor
        if self.horas_semanais:
            total_horas = ParticipacaoServidor.objects.filter(
                servidor=self.servidor,
                semestre=self.semestre
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('horas_semanais')
            )['total'] or 0

            if total_horas + float(self.horas_semanais) > 12:
                raise ValidationError(
                    f'Servidor já possui {total_horas}h/semana em outros projetos. '
                    f'Total não pode exceder 12h semanais.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ParticipacaoEstudante(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)
    estudante = models.ForeignKey(Estudante, on_delete=models.CASCADE)
    bolsista = models.BooleanField(default=False)
    valor_bolsa = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['projeto', 'estudante']
        verbose_name = 'Participação de Estudante'
        verbose_name_plural = 'Participações de Estudantes'
        ordering = ['estudante__nome']

    def __str__(self):
        return f"{self.estudante.nome} - {self.projeto.titulo}"

    def clean(self):
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError('Data fim não pode ser anterior à data início.')


class AlertaRelatorio(models.Model):
    TIPO_CHOICES = [
        ('PROXIMO', 'Próximo do prazo'),
        ('VENCIDO', 'Prazo vencido'),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='alertas')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    data_alerta = models.DateField()
    visualizado = models.BooleanField(default=False)
    data_visualizacao = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerta de Relatório'
        verbose_name_plural = 'Alertas de Relatórios'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.projeto.titulo}"

    def marcar_visualizado(self):
        self.visualizado = True
        self.data_visualizacao = timezone.now()
        self.save()


# Registrar no auditlog
auditlog.register(Projeto)
auditlog.register(ParticipacaoServidor)
auditlog.register(ParticipacaoEstudante)