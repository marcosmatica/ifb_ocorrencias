# atendimentos/models.py

from django.db import models
from core.models import Estudante, Servidor


class TipoAtendimento(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)


class SituacaoAtendimento(models.Model):
    nome = models.CharField(max_length=100)
    cor = models.CharField(max_length=7, default='#6b7280')  # Hex color
    ativo = models.BooleanField(default=True)


class Atendimento(models.Model):
    COORDENACAO_CHOICES = [
        ('CDPD', 'Coordenação Pedagógica'),
        ('CC', 'Coordenação de Curso'),
        ('CDRA', 'Coordenação de Registro Acadêmico'),
        ('NAPNE', 'NAPNE'),
        ('CDAE', 'Coordenação de Assistência Estudantil'),
        ('CDAE_PEDAGOGICO', 'CDAE - Pedagógico'),
        ('CDAE_ASSISTENCIA', 'CDAE - Assistência Estudantil'),
        ('CDAE_PSICOLOGA', 'CDAE - Psicóloga'),
        ('CDBA', 'Coordenação de Biblioteca'),
        ('CGEN', 'Coordenação Geral'),
        ('CGEN', 'Docente'),
        ('DREP', 'Direção de Ensino'),
        ('DG', 'Direção Geral'),
    ]

    ORIGEM_CHOICES = [
        ('ESPONTANEO', 'Espontâneo'),
        ('ENCAMINHAMENTO', 'Encaminhamento'),
        ('SOLICITACAO_DOCENTE', 'Solicitação de Docente'),
        ('SOLICITACAO_COORDENACAO', 'Solicitação de Coordenação'),
        ('OUTRO', 'Outro'),
    ]

    coordenacao = models.CharField(max_length=30, choices=COORDENACAO_CHOICES)
    estudantes = models.ManyToManyField(Estudante, related_name='atendimentos')
    servidor_responsavel = models.ForeignKey(Servidor, on_delete=models.PROTECT, related_name='atendimentos_realizados')
    servidores_participantes = models.ManyToManyField(Servidor, related_name='atendimentos_participacao', blank=True)

    data = models.DateField()
    hora = models.TimeField()

    tipo_atendimento = models.ForeignKey(TipoAtendimento, on_delete=models.PROTECT)
    situacao = models.ForeignKey(SituacaoAtendimento, on_delete=models.PROTECT)
    origem = models.CharField(max_length=30, choices=ORIGEM_CHOICES)

    informacoes = models.TextField()
    observacoes = models.TextField(blank=True)
    anexos = models.FileField(upload_to='atendimentos/', blank=True, null=True)

    publicar_ficha_aluno = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-hora']
        verbose_name = 'Atendimento'
        verbose_name_plural = 'Atendimentos'