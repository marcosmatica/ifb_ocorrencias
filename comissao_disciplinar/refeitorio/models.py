from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from auditlog.registry import auditlog
from core.models import Estudante, Servidor


class ConfigRefeitorio(models.Model):
    """Configuração de horários e regras do refeitório"""
    TIPO_REFEICAO_CHOICES = [
        ('CAFE', 'Café da Manhã'),
        ('ALMOCO', 'Almoço'),
        ('LANCHE', 'Lanche da Tarde'),
        ('JANTAR', 'Jantar'),
    ]

    nome = models.CharField(max_length=50, choices=TIPO_REFEICAO_CHOICES, unique=True)
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()
    ativo = models.BooleanField(default=True)
    intervalo_minimo_horas = models.IntegerField(
        default=3,
        help_text="Intervalo mínimo em horas entre refeições do mesmo tipo"
    )

    class Meta:
        verbose_name = "Configuração de Refeitório"
        verbose_name_plural = "Configurações de Refeitório"
        ordering = ['horario_inicio']

    def __str__(self):
        return f"{self.get_nome_display()} ({self.horario_inicio} - {self.horario_fim})"

    def esta_no_horario(self):
        """Verifica se está no horário desta refeição"""
        agora = timezone.localtime(timezone.now()).time()  # ← Converte para America/Sao_Paulo
        return self.horario_inicio <= agora <= self.horario_fim


class RegistroRefeicao(models.Model):
    """Registro de acesso ao refeitório"""
    # Relacionamento flexível
    estudante = models.ForeignKey(
        Estudante,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='refeicoes'
    )
    servidor = models.ForeignKey(
        Servidor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='refeicoes'
    )

    tipo_refeicao = models.CharField(max_length=20)
    data_hora = models.DateTimeField(auto_now_add=True)

    # Dados extras para auditoria
    codigo_barras_usado = models.CharField(max_length=50, blank=True)
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de Refeição"
        verbose_name_plural = "Registros de Refeições"
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['data_hora', 'estudante']),
            models.Index(fields=['data_hora', 'servidor']),
        ]

    def __str__(self):
        pessoa = self.estudante or self.servidor
        nome = pessoa.nome if pessoa else "Desconhecido"
        return f"{nome} - {self.tipo_refeicao} em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    def clean(self):
        """Validação: deve ter estudante OU servidor, não ambos"""
        if not self.estudante and not self.servidor:
            raise ValidationError('Deve informar estudante ou servidor.')
        if self.estudante and self.servidor:
            raise ValidationError('Não pode informar ambos estudante e servidor.')

    @property
    def pessoa(self):
        """Retorna o objeto pessoa (estudante ou servidor)"""
        return self.estudante or self.servidor

    @property
    def tipo_pessoa(self):
        """Retorna o tipo de pessoa"""
        return "Estudante" if self.estudante else "Servidor"


class BloqueioAcesso(models.Model):
    """Bloqueios temporários ou permanentes de acesso ao refeitório"""
    estudante = models.ForeignKey(
        Estudante,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bloqueios_refeitorio'
    )
    servidor = models.ForeignKey(
        Servidor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bloqueios_refeitorio'
    )

    motivo = models.TextField()
    data_inicio = models.DateField(default=timezone.now)
    data_fim = models.DateField(null=True, blank=True, help_text="Deixe em branco para bloqueio permanente")
    ativo = models.BooleanField(default=True)

    criado_por = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='bloqueios_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bloqueio de Acesso"
        verbose_name_plural = "Bloqueios de Acesso"
        ordering = ['-criado_em']

    def __str__(self):
        pessoa = self.estudante or self.servidor
        return f"Bloqueio: {pessoa.nome if pessoa else 'N/A'} - {self.motivo[:50]}"

    def clean(self):
        if not self.estudante and not self.servidor:
            raise ValidationError('Deve informar estudante ou servidor.')
        if self.estudante and self.servidor:
            raise ValidationError('Não pode informar ambos.')

    def esta_ativo(self):
        """Verifica se o bloqueio está vigente"""
        if not self.ativo:
            return False
        hoje = timezone.now().date()
        if self.data_fim:
            return self.data_inicio <= hoje <= self.data_fim
        return self.data_inicio <= hoje


# Registrar no auditlog
auditlog.register(RegistroRefeicao)
auditlog.register(ConfigRefeitorio)
auditlog.register(BloqueioAcesso)