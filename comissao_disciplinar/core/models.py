from django.db import models
from django.contrib.auth.models import User
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField
from django.core.validators import RegexValidator
from django.utils import timezone


# ====================
# CLASSES HELPER
# ====================

class Coordenacao:
    """Choices centralizadas para coordenações"""
    CHOICES = [
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
        ('DOCENTE', 'Docente'),
        ('DREP', 'Direção de Ensino, Pesquisa e Extensão'),
        ('DG', 'Direção Geral'),
    ]


# ====================
# MODELS INSTITUCIONAIS
# ====================

class Campus(models.Model):
    nome = models.CharField(max_length=100)
    sigla = models.CharField(max_length=10)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Campi"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Curso(models.Model):
    nome = models.CharField(max_length=200)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name='cursos')
    codigo = models.CharField(max_length=20, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.campus.sigla}"


class Turma(models.Model):
    nome = models.CharField(max_length=50)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    ano = models.IntegerField()
    periodo = models.CharField(max_length=20)  # "2024.1", "2024.2"
    semestre = models.IntegerField(choices=[(0, 'Anual'), (1, '1º'), (2, '2º')])
    sala = models.CharField(max_length=20, blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-ano', '-semestre', 'nome']
        unique_together = ['nome', 'curso', 'ano', 'semestre']

    def __str__(self):
        return f"{self.nome} - {self.ano}/{self.semestre}"


# ====================
# PESSOAS
# ====================

# models.py - Modelo Responsavel corrigido
class Responsavel(models.Model):
    TIPO_VINCULO_CHOICES = [
        ('PAI', 'Pai'),
        ('MAE', 'Mãe'),
        ('TUTOR', 'Tutor Legal'),
        ('OUTRO', 'Outro'),
    ]
    PREFERENCIA_CONTATO_CHOICES = [
        ('EMAIL', 'E-mail'),
        ('CELULAR', 'Celular'),
        ('WHATSAPP', 'WhatsApp'),
    ]

    nome = models.CharField(max_length=200)
    email = models.EmailField()
    celular = models.CharField(max_length=15, validators=[
        RegexValidator(r'^\+?1?\d{9,15}$', 'Número de telefone inválido.')
    ])
    endereco = models.TextField(blank=True)
    tipo_vinculo = models.CharField(max_length=10, choices=TIPO_VINCULO_CHOICES)
    preferencia_contato = models.CharField(
        max_length=10,
        choices=PREFERENCIA_CONTATO_CHOICES,
        default='EMAIL'
    )

    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Responsáveis"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_vinculo_display()})"

    @property
    def estudantes(self):
        """Retorna todos os estudantes vinculados a este responsável"""
        return self.estudantes.all()

    @property
    def estudantes_ativos(self):
        """Retorna estudantes ativos vinculados"""
        return self.estudantes.filter(situacao='ATIVO')

    @property
    def total_estudantes(self):
        """Retorna o total de estudantes vinculados"""
        return self.estudantes.count()


class Estudante(models.Model):
    SITUACAO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('TRANCADO', 'Trancado'),
        ('EVADIDO', 'Evadido'),
        ('FORMADO', 'Formado'),
        ('TRANSFERIDO', 'Transferido'),
    ]

    # Identificação
    matricula_sga = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

    # Contatos
    email = models.EmailField()

    # Endereço
    cep = models.CharField(max_length=15, blank=True)
    logradouro = models.CharField(max_length=200, blank=True)
    bairro_cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)


    # Acadêmico
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='estudantes')
    turma_periodo = models.CharField(max_length=20, blank=True)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    situacao = models.CharField(max_length=15, choices=SITUACAO_CHOICES, default='ATIVO')
    data_ingresso = models.DateField()

    # Foto - MANTÉM O CAMPO ORIGINAL para upload local
    foto = models.ImageField(upload_to='estudantes/', blank=True, null=True)

    # NOVO CAMPO - URL da foto do Google Drive
    foto_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link direto da imagem no Google Drive. Use o formato: https://drive.google.com/uc?export=view&id=ID_DA_IMAGEM"
    )

    # Responsável
    responsaveis = models.ManyToManyField(
        Responsavel,
        related_name='estudantes',
        blank=True
    )

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.matricula_sga})"

    def get_foto_url(self):
        """Retorna a URL da foto (prioriza foto_url, depois foto local)"""
        if self.foto_url:
            return self.foto_url
        elif self.foto:
            return self.foto.url
        return None

    def get_foto_url_proxy(self):
        """Retorna a URL da foto usando proxy para Google Drive"""
        from django.urls import reverse

        if self.foto_url and 'drive.google.com' in self.foto_url:
            # Extrair ID do Google Drive
            import re
            match = re.search(r'id=([^&]+)', self.foto_url)
            if match:
                file_id = match.group(1)
                return reverse('core:proxy_google_drive_image') + f'?id={file_id}'

        # Se for foto local ou não for Google Drive, retornar URL normal
        return self.get_foto_url()

    def get_iniciais(self):
        """Retorna as iniciais do nome para avatar"""
        partes = self.nome.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        return self.nome[0].upper() if self.nome else "?"


class Servidor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    siape = models.CharField(max_length=10, unique=True)
    nome = models.CharField(max_length=200)
    funcao = models.CharField(max_length=100)
    email = models.EmailField()
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT)
    coordenacao = models.CharField(
        max_length=30,
        choices=Coordenacao.CHOICES,
        blank=True
    )
    membro_comissao_disciplinar = models.BooleanField(default=False)
    pode_registrar_atendimento = models.BooleanField(default=False)
    pode_visualizar_ficha_aluno = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Servidores"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.siape}"


# ====================
# INFRAÇÕES E SANÇÕES
# ====================

class Infracao(models.Model):
    GRAVIDADE_CHOICES = [
        ('LEVE', 'Leve'),
        ('MEDIA', 'Média'),
        ('GRAVE', 'Grave'),
        ('GRAVISSIMA', 'Gravíssima'),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.TextField()
    gravidade = models.CharField(max_length=15, choices=GRAVIDADE_CHOICES)
    referencia_artigo = models.CharField(
        max_length=50,
        help_text="Art. XX do Regulamento"
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Infração"
        verbose_name_plural = "Infrações"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descricao[:50]}"


class Sancao(models.Model):
    TIPO_CHOICES = [
        ('ADVERTENCIA_VERBAL', 'Advertência Verbal'),
        ('ADVERTENCIA_ESCRITA', 'Advertência Escrita'),
        ('SUSPENSAO', 'Suspensão'),
        ('TRANSFERENCIA', 'Transferência Compulsória'),
        ('DESLIGAMENTO', 'Desligamento'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    descricao = models.TextField()
    infraccoes = models.ManyToManyField(Infracao, related_name='sancoes_previstas')

    class Meta:
        verbose_name = "Sanção"
        verbose_name_plural = "Sanções"

    def __str__(self):
        return self.get_tipo_display()


# ====================
# OCORRÊNCIAS
# ====================

class Ocorrencia(models.Model):
    STATUS_CHOICES = [
        ('REGISTRADA', 'Registrada'),
        ('EM_ANALISE', 'Em Análise Prévia'),
        ('COMISSAO_DESIGNADA', 'Comissão Designada'),
        ('ESTUDANTE_NOTIFICADO', 'Estudante Notificado'),
        ('AGUARDANDO_DEFESA', 'Aguardando Defesa'),
        ('DEFESA_APRESENTADA', 'Defesa Apresentada'),
        ('EM_JULGAMENTO', 'Em Julgamento'),
        ('SANCAO_APLICADA', 'Sanção Aplicada'),
        ('EM_RECURSO', 'Em Recurso'),
        ('FINALIZADA', 'Finalizada'),
        ('ARQUIVADA', 'Arquivada'),
    ]

    # Dados básicos
    data = models.DateField(default=timezone.now)
    horario = models.TimeField()
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT)
    estudantes = models.ManyToManyField(Estudante, related_name='ocorrencias')
    testemunhas = models.TextField(
        blank=True,
        help_text="Nome das testemunhas, separadas por vírgula"
    )

    # Descrição e classificação
    descricao = models.TextField()
    infracao = models.ForeignKey(Infracao, on_delete=models.PROTECT, null=True, blank=True)
    evidencias = models.FileField(upload_to='evidencias/', blank=True, null=True)

    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REGISTRADA')

    # Prazos e defesa
    prazo_defesa = models.DateField(null=True, blank=True)
    data_defesa = models.DateField(null=True, blank=True)
    defesa_texto = models.TextField(blank=True)
    defesa_arquivo = models.FileField(upload_to='defesas/', blank=True, null=True)

    # Medidas e sanções
    medida_preventiva = models.TextField(blank=True)
    sancao = models.ForeignKey(
        Sancao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ocorrencias'
    )
    sancao_detalhes = models.TextField(blank=True)

    # Registro
    responsavel_registro = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='ocorrencias_registradas'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # Auditlog
    history = AuditlogHistoryField()

    # Notificações
    usuarios_interessados = models.ManyToManyField(
        User,
        related_name='ocorrencias_interesse',
        blank=True
    )
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ['-data', '-horario']

    def __str__(self):
        return f"Ocorrência #{self.id} - {self.data} - {self.get_status_display()}"

    @property
    def flow(self):
        return OcorrenciaFlow(self)


class OcorrenciaFlow:
    """Flow handler para transições de estado"""
    def __init__(self, ocorrencia_instance):
        self.ocorrencia = ocorrencia_instance

    def iniciar_analise(self):
        if self.ocorrencia.status == 'REGISTRADA':
            self.ocorrencia.status = 'EM_ANALISE'
            self.ocorrencia.save()

    def designar_comissao(self):
        if self.ocorrencia.status == 'EM_ANALISE':
            self.ocorrencia.status = 'COMISSAO_DESIGNADA'
            self.ocorrencia.save()

    def notificar_estudante(self):
        if self.ocorrencia.status in ['COMISSAO_DESIGNADA', 'REGISTRADA']:
            from datetime import timedelta
            self.ocorrencia.status = 'ESTUDANTE_NOTIFICADO'
            self.ocorrencia.prazo_defesa = timezone.now().date() + timedelta(days=5)
            self.ocorrencia.save()

    def aguardar_defesa(self):
        if self.ocorrencia.status == 'ESTUDANTE_NOTIFICADO':
            self.ocorrencia.status = 'AGUARDANDO_DEFESA'
            self.ocorrencia.save()

    def registrar_defesa(self):
        if self.ocorrencia.status == 'AGUARDANDO_DEFESA':
            self.ocorrencia.status = 'DEFESA_APRESENTADA'
            self.ocorrencia.data_defesa = timezone.now().date()
            self.ocorrencia.save()

    def iniciar_julgamento(self):
        if self.ocorrencia.status in ['DEFESA_APRESENTADA', 'AGUARDANDO_DEFESA']:
            self.ocorrencia.status = 'EM_JULGAMENTO'
            self.ocorrencia.save()

    def aplicar_sancao(self):
        if self.ocorrencia.status == 'EM_JULGAMENTO':
            self.ocorrencia.status = 'SANCAO_APLICADA'
            self.ocorrencia.save()

    def abrir_recurso(self):
        if self.ocorrencia.status == 'SANCAO_APLICADA':
            self.ocorrencia.status = 'EM_RECURSO'
            self.ocorrencia.save()

    def finalizar(self):
        if self.ocorrencia.status in ['SANCAO_APLICADA', 'EM_RECURSO', 'REGISTRADA']:
            self.ocorrencia.status = 'FINALIZADA'
            self.ocorrencia.save()

    def arquivar(self):
        self.ocorrencia.status = 'ARQUIVADA'
        self.ocorrencia.save()


# ====================
# COMISSÃO E PROCESSOS
# ====================

class ComissaoProcessoDisciplinar(models.Model):
    ocorrencia = models.OneToOneField(
        Ocorrencia,
        on_delete=models.CASCADE,
        related_name='comissao'
    )
    membros = models.ManyToManyField(Servidor, related_name='comissoes')
    presidente = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='comissoes_presididas'
    )
    data_instauracao = models.DateField(auto_now_add=True)
    data_conclusao = models.DateField(null=True, blank=True)
    parecer_final = models.TextField(blank=True)

    class Meta:
        verbose_name = "Comissão de Processo Disciplinar"
        verbose_name_plural = "Comissões de Processos Disciplinares"

    def __str__(self):
        return f"Comissão - Ocorrência #{self.ocorrencia.id}"


class NotificacaoOficial(models.Model):
    TIPO_CHOICES = [
        ('NOTIFICACAO', 'Notificação'),
        ('INTIMACAO', 'Intimação'),
        ('COMUNICADO', 'Comunicado'),
    ]
    MEIO_ENVIO_CHOICES = [
        ('EMAIL', 'E-mail'),
        ('CORREIO', 'Correio'),
        ('PRESENCIAL', 'Presencial'),
        ('WHATSAPP', 'WhatsApp'),
    ]

    ocorrencia = models.ForeignKey(
        Ocorrencia,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    destinatarios = models.TextField(help_text="E-mails separados por vírgula")
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    data_envio = models.DateTimeField(auto_now_add=True)
    data_recebimento = models.DateTimeField(null=True, blank=True)
    meio_envio = models.CharField(max_length=15, choices=MEIO_ENVIO_CHOICES)
    comprovante = models.FileField(upload_to='comprovantes/', blank=True, null=True)
    texto = models.TextField()

    class Meta:
        verbose_name = "Notificação Oficial"
        verbose_name_plural = "Notificações Oficiais"
        ordering = ['-data_envio']

    def __str__(self):
        return f"{self.get_tipo_display()} - Ocorrência #{self.ocorrencia.id}"


class Recurso(models.Model):
    RESULTADO_CHOICES = [
        ('DEFERIDO', 'Deferido'),
        ('PARCIALMENTE_DEFERIDO', 'Parcialmente Deferido'),
        ('INDEFERIDO', 'Indeferido'),
        ('PENDENTE', 'Pendente'),
    ]

    ocorrencia = models.ForeignKey(
        Ocorrencia,
        on_delete=models.CASCADE,
        related_name='recursos'
    )
    data_protocolo = models.DateTimeField(auto_now_add=True)
    argumentacao = models.TextField()
    documentos_anexos = models.FileField(upload_to='recursos/', blank=True, null=True)
    parecer_recurso = models.TextField(blank=True)
    data_decisao = models.DateField(null=True, blank=True)
    resultado = models.CharField(max_length=25, choices=RESULTADO_CHOICES, default='PENDENTE')

    class Meta:
        ordering = ['-data_protocolo']

    def __str__(self):
        return f"Recurso - Ocorrência #{self.ocorrencia.id}"


class DocumentoGerado(models.Model):
    TIPO_CHOICES = [
        ('REGISTRO', 'Registro de Ocorrência'),
        ('ATA_ADVERTENCIA', 'Ata de Advertência'),
        ('TERMO_COMPROMISSO', 'Termo de Compromisso'),
        ('NOTIFICACAO', 'Notificação/Intimação'),
        ('PARECER', 'Parecer da Comissão'),
        ('RECIBO_TERMICO', 'Recibo Térmico'),  # NOVO
    ]

    # Relacionamentos (um dos dois deve estar preenchido)
    ocorrencia = models.ForeignKey(
        Ocorrencia,
        on_delete=models.CASCADE,
        related_name='documentos',
        null=True,
        blank=True
    )

    # NOVO: Relacionamento com OcorrenciaRapida
    ocorrencia_rapida = models.ForeignKey(
        'OcorrenciaRapida',
        on_delete=models.CASCADE,
        related_name='documentos',
        null=True,
        blank=True
    )

    tipo_documento = models.CharField(max_length=25, choices=TIPO_CHOICES)
    arquivo = models.FileField(upload_to='documentos_gerados/')
    data_geracao = models.DateTimeField(auto_now_add=True)
    assinado = models.BooleanField(default=False)
    assinaturas = models.ManyToManyField(
        Servidor,
        related_name='documentos_assinados',
        blank=True
    )
    qrcode = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    class Meta:
        ordering = ['-data_geracao']

    def __str__(self):
        if self.ocorrencia:
            return f"{self.get_tipo_documento_display()} - Ocorrência #{self.ocorrencia.id}"
        elif self.ocorrencia_rapida:
            return f"{self.get_tipo_documento_display()} - Ocorrência Rápida #{self.ocorrencia_rapida.id}"
        return f"{self.get_tipo_documento_display()}"

    def clean(self):
        """Validação para garantir que pelo menos uma ocorrência está vinculada"""
        from django.core.exceptions import ValidationError
        if not self.ocorrencia and not self.ocorrencia_rapida:
            raise ValidationError('Documento deve estar vinculado a uma Ocorrência ou Ocorrência Rápida.')
        if self.ocorrencia and self.ocorrencia_rapida:
            raise ValidationError('Documento não pode estar vinculado a ambos os tipos de ocorrência.')


# ====================
# NOTIFICAÇÕES DO SISTEMA
# ====================

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('NOVA_OCORRENCIA', 'Nova Ocorrência'),
        ('ATUALIZACAO_STATUS', 'Atualização de Status'),
        ('COMENTARIO', 'Novo Comentário'),
        ('PRAZO', 'Lembrete de Prazo'),
        ('DEFESA', 'Defesa Apresentada'),
        ('SANCAO', 'Sanção Aplicada'),
    ]

    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    ocorrencia = models.ForeignKey(
        'Ocorrencia',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    lida = models.BooleanField(default=False)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='MEDIA')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"


class PreferenciaNotificacao(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferencias_notificacao'
    )
    receber_email_novas_ocorrencias = models.BooleanField(default=True)
    receber_email_atualizacoes = models.BooleanField(default=True)
    receber_email_prazos = models.BooleanField(default=True)
    receber_notificacoes_urgentes = models.BooleanField(default=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferências de {self.usuario.username}"


# ====================
# OCORRÊNCIAS RÁPIDAS
# ====================

class OcorrenciaRapida(models.Model):
    TIPOS_RAPIDOS = [
        ('ATRASO', 'Atraso para apresentar-se à aula designada'),
        ('CELULAR', 'Uso indevido de celular durante aula'),
        ('UNIFORME', 'Sem uniforme nos espaços do campus em horário de aula'),
        ('UNIFORME_RETIRADA', 'Retirou uniforme após apresentar-se na recepção'),
        ('RECUSA', 'Recusa a participar das atividades propostas pela(o) docente ou Coordenação'),
        ('AUSENCIA', 'Ausência de sala em período de aula'),
        ('SAIDA', 'Saída Antecipada do campus'),
        ('BIBLIO', 'Acesso a Biblioteca sem autorização prévia de docentes e/ou Coordenação'),
    ]

    # Dados básicos
    data = models.DateField(default=timezone.now)
    horario = models.TimeField()
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT)
    estudantes = models.ManyToManyField(Estudante, related_name='ocorrencias_rapidas')

    # ALTERADO: Agora é ManyToManyField para permitir múltiplos tipos
    tipos_rapidos = models.ManyToManyField(
        'TipoOcorrenciaRapida',
        related_name='ocorrencias_rapidas',
        verbose_name='Tipos de Ocorrência Rápida'
    )

    # Descrição gerada automaticamente
    descricao = models.TextField(blank=True)

    # Registro
    responsavel_registro = models.ForeignKey(
        Servidor,
        on_delete=models.PROTECT,
        related_name='ocorrencias_rapidas_registradas'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # Auditlog
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Ocorrência Rápida"
        verbose_name_plural = "Ocorrências Rápidas"
        ordering = ['-data', '-horario']

    def __str__(self):
        return f"Ocorrência Rápida #{self.id} - {self.data}"

    def save(self, *args, **kwargs):
        """Gera descrição automaticamente baseada nos tipos selecionados"""
        if not self.descricao and hasattr(self, 'tipos_rapidos'):
            tipos_selecionados = self.tipos_rapidos.all()
            descricoes = [tipo.descricao for tipo in tipos_selecionados]
            self.descricao = "; ".join(descricoes)

        # Define o curso automaticamente baseado na turma
        if self.turma and not hasattr(self, '_curso'):
            self._curso = self.turma.curso

        super().save(*args, **kwargs)

    @property
    def curso(self):
        """Propriedade para compatibilidade com as views existentes"""
        return self.turma.curso if self.turma else None

    def get_tipos_display(self):
        """Retorna a lista de tipos formatados para exibição"""
        return [tipo.get_tipo_display() for tipo in self.tipos_rapidos.all()]


# NOVO MODELO para os tipos de ocorrência rápida
class TipoOcorrenciaRapida(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.TextField()
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de Ocorrência Rápida"
        verbose_name_plural = "Tipos de Ocorrência Rápida"

    def __str__(self):
        return f"{self.codigo} - {self.descricao[:50]}"

    def get_tipo_display(self):
        """Retorna a descrição formatada"""
        return f"{self.codigo}: {self.descricao}"

# ====================
# REGISTRO NO AUDITLOG
# ====================

auditlog.register(Ocorrencia)
auditlog.register(Estudante)
auditlog.register(ComissaoProcessoDisciplinar)
auditlog.register(DocumentoGerado)
auditlog.register(OcorrenciaRapida)