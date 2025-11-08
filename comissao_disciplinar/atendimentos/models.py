from django.db import models
from core.models import Estudante, Servidor, Coordenacao


class TipoAtendimento(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo de Atendimento'
        verbose_name_plural = 'Tipos de Atendimento'

    def __str__(self):
        return self.nome


class SituacaoAtendimento(models.Model):
    nome = models.CharField(max_length=100)
    cor = models.CharField(max_length=7, default='#6b7280')
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Situação de Atendimento'
        verbose_name_plural = 'Situações de Atendimento'

    def __str__(self):
        return self.nome


class Atendimento(models.Model):
    ORIGEM_CHOICES = [
        ('PRESENCIAL', 'Presencial'),
        ('ENCAMINHAMENTO', 'Encaminhamento'),
        ('SOLICITACAO_DOCENTE', 'Solicitação de Docente'),
        ('SOLICITACAO_COORDENACAO', 'Solicitação de Coordenação'),
        ('CONTATO_TELEFONICO', 'Contato Telefônico'),
        ('CONTATO_WHATSAPP', 'Contato Whatsapp'),
        ('RESPONSAVEL', 'Responsável'),
        ('OUTRO', 'Outro'),
    ]

    # Coordenação usa choices do core
    coordenacao = models.CharField(max_length=30, choices=Coordenacao.CHOICES)

    # Relacionamentos com core
    estudantes = models.ManyToManyField(Estudante, related_name='atendimentos')
    servidor_responsavel = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='atendimentos_realizados'
    )
    servidores_participantes = models.ManyToManyField(
        Servidor,
        related_name='atendimentos_participacao',
        blank=True
    )

    # Dados do atendimento
    data = models.DateField()
    hora = models.TimeField()
    tipo_atendimento = models.ForeignKey(TipoAtendimento, on_delete=models.PROTECT)
    situacao = models.ForeignKey(SituacaoAtendimento, on_delete=models.PROTECT)
    origem = models.CharField(max_length=30, choices=ORIGEM_CHOICES)
    informacoes = models.TextField()
    observacoes = models.TextField(blank=True)
    anexos = models.FileField(upload_to='atendimentos/', blank=True, null=True)
    publicar_ficha_aluno = models.BooleanField(default=False)

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-hora']
        verbose_name = 'Atendimento'
        verbose_name_plural = 'Atendimentos'

    def __str__(self):
        return f"Atendimento #{self.id} - {self.data}"