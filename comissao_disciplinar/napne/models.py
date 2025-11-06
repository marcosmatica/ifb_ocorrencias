from django.db import models
from core.models import Estudante, Servidor, Turma

class FichaEstudanteNAPNE(models.Model):
    """Ficha do estudante no NAPNE"""
    estudante = models.OneToOneField(Estudante, on_delete=models.CASCADE, related_name='ficha_napne')
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT)
    necessidade_especifica = models.TextField()
    telefone = models.CharField(max_length=20)
    atendido_por = models.ForeignKey(Servidor, on_delete=models.PROTECT, related_name='estudantes_napne')
    laudo_apresentado = models.BooleanField(default=False)
    emails_enviados = models.TextField(blank=True, help_text="Log de emails enviados")
    observacoes_laudos_historico = models.TextField(blank=True, help_text="Histórico de observações dos laudos")
    observacao_laudo_atual = models.TextField(blank=True, help_text="Observação atual do laudo")
    
    # Desempenho por bimestre
    desempenho_1bim = models.TextField(blank=True)
    desempenho_2bim = models.TextField(blank=True)
    desempenho_3bim = models.TextField(blank=True)
    desempenho_4bim = models.TextField(blank=True)
    resultado_final = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ficha NAPNE'
        verbose_name_plural = 'Fichas NAPNE'
        ordering = ['estudante__nome']
    
    def __str__(self):
        return f"Ficha NAPNE - {self.estudante.nome}"
    
    def adicionar_observacao_laudo(self, nova_observacao):
        """Adiciona nova observação ao histórico e atualiza a atual"""
        if self.observacao_laudo_atual:
            timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
            self.observacoes_laudos_historico += f"\n[{timestamp}] {self.observacao_laudo_atual}"
        self.observacao_laudo_atual = nova_observacao
        self.save()


class TipoAtendimentoNAPNE(models.Model):
    """Tipos de atendimento do NAPNE"""
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Tipo de Atendimento NAPNE'
        verbose_name_plural = 'Tipos de Atendimento NAPNE'
    
    def __str__(self):
        return self.nome


class NecessidadeEspecifica(models.Model):
    """Necessidades específicas para seleção múltipla"""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Necessidade Específica'
        verbose_name_plural = 'Necessidades Específicas'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class SetorEncaminhamento(models.Model):
    """Setores para encaminhamento"""
    nome = models.CharField(max_length=100)
    sigla = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Setor de Encaminhamento'
        verbose_name_plural = 'Setores de Encaminhamento'
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class StatusAtendimentoNAPNE(models.Model):
    """Status dos atendimentos NAPNE"""
    nome = models.CharField(max_length=100)
    cor = models.CharField(max_length=7, default='#6b7280')
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Status de Atendimento NAPNE'
        verbose_name_plural = 'Status de Atendimentos NAPNE'
    
    def __str__(self):
        return self.nome


class AtendimentoNAPNE(models.Model):
    """Atendimentos do NAPNE"""
    ORIGEM_CHOICES = [
        ('ESPONTANEO', 'Espontâneo'),
        ('ENCAMINHAMENTO', 'Encaminhamento'),
        ('SOLICITACAO_DOCENTE', 'Solicitação de Docente'),
        ('SOLICITACAO_COORDENACAO', 'Solicitação de Coordenação'),
        ('OUTRO', 'Outro'),
    ]
    
    estudante = models.ForeignKey(Estudante, on_delete=models.PROTECT, related_name='atendimentos_napne')
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT)
    origem = models.CharField(max_length=30, choices=ORIGEM_CHOICES)
    data = models.DateField()
    atendido_por = models.ForeignKey(Servidor, on_delete=models.PROTECT, related_name='atendimentos_napne_realizados')
    tipo_atendimento = models.ForeignKey(TipoAtendimentoNAPNE, on_delete=models.PROTECT)
    laudo_previo = models.ForeignKey(FichaEstudanteNAPNE, on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos')
    necessidades_especificas = models.ManyToManyField(NecessidadeEspecifica, blank=True)
    detalhamento = models.TextField(verbose_name="Detalhamento do Atendimento")
    acoes = models.TextField(verbose_name="Ações Realizadas")
    resumo_atendimento = models.TextField(blank=True)
    publicar_ficha_aluno = models.BooleanField(default=False, verbose_name="Publicar na Ficha do Aluno")
    status = models.ForeignKey(StatusAtendimentoNAPNE, on_delete=models.PROTECT)
    data_ultima_atualizacao_status = models.DateTimeField(auto_now=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Atendimento NAPNE'
        verbose_name_plural = 'Atendimentos NAPNE'
        ordering = ['-data']
    
    def __str__(self):
        return f"Atendimento NAPNE #{self.id} - {self.estudante.nome} - {self.data}"


class ObservacaoEncaminhamento(models.Model):
    """Observações de direcionamento para setores"""
    atendimento = models.ForeignKey(AtendimentoNAPNE, on_delete=models.CASCADE, related_name='observacoes_encaminhamento')
    setor = models.ForeignKey(SetorEncaminhamento, on_delete=models.PROTECT)
    observacao = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Observação de Encaminhamento'
        verbose_name_plural = 'Observações de Encaminhamento'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"Encaminhamento para {self.setor.sigla} - Atendimento #{self.atendimento.id}"