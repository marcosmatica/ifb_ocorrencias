from django.contrib import admin
from .models import *
from django.utils.html import format_html







@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ['siape', 'nome', 'funcao', 'membro_comissao_disciplinar']
    list_filter = ['membro_comissao_disciplinar', 'campus']
    search_fields = ['nome', 'siape']


@admin.register(Infracao)
class InfracaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'gravidade', 'ativo']
    list_filter = ['gravidade', 'ativo']
    search_fields = ['codigo', 'descricao']


@admin.register(Sancao)
class SancaoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'descricao']
    filter_horizontal = ['infraccoes']


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'data', 'status', 'curso', 'turma', 'responsavel_registro']
    list_filter = ['status', 'data', 'curso', 'infracao__gravidade']
    search_fields = ['descricao', 'estudantes__nome']
    date_hierarchy = 'data'


@admin.register(ComissaoProcessoDisciplinar)
class ComissaoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'presidente', 'data_instauracao', 'data_conclusao']
    filter_horizontal = ['membros']


@admin.register(NotificacaoOficial)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'tipo', 'data_envio', 'meio_envio']
    list_filter = ['tipo', 'meio_envio']


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'data_protocolo', 'resultado', 'data_decisao']
    list_filter = ['resultado']


@admin.register(DocumentoGerado)
class DocumentoGeradoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'tipo_documento', 'data_geracao', 'assinado']
    list_filter = ['tipo_documento', 'assinado']


@admin.register(OcorrenciaRapida)
class OcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'data',
        'horario',
        'turma',
        'listar_tipos',  # Novo método para listar os tipos
        'quantidade_estudantes',
        'responsavel_registro'
    ]
    list_filter = [
        'data',
        'turma__curso__campus',
        'tipos_rapidos'  # Agora filtra pelos tipos (ManyToMany)
    ]
    search_fields = [
        'estudantes__nome',
        'estudantes__matricula_sga',
        'descricao',
        'tipos_rapidos__codigo',
        'tipos_rapidos__descricao'
    ]
    date_hierarchy = 'data'
    filter_horizontal = ['tipos_rapidos', 'estudantes']  # Adicionado para facilitar a seleção

    # Campos para exibição no formulário de edição
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('data', 'horario', 'turma')
        }),
        ('Tipos de Ocorrência', {
            'fields': ('tipos_rapidos',),
            'description': 'Selecione um ou mais tipos de ocorrência rápida'
        }),
        ('Estudantes Envolvidos', {
            'fields': ('estudantes',),
            'description': 'Selecione os estudantes envolvidos na ocorrência'
        }),
        ('Descrição Automática', {
            'fields': ('descricao',),
            'classes': ('collapse',),
            'description': 'Descrição gerada automaticamente baseada nos tipos selecionados'
        }),
        ('Registro', {
            'fields': ('responsavel_registro', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['descricao', 'criado_em', 'atualizado_em']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'turma', 'turma__curso', 'responsavel_registro'
        ).prefetch_related('estudantes', 'tipos_rapidos')

    def listar_tipos(self, obj):
        """Lista os tipos de ocorrência rápida associados"""
        tipos = obj.tipos_rapidos.all()
        if tipos:
            return ", ".join([tipo.codigo for tipo in tipos])
        return "Nenhum tipo"

    listar_tipos.short_description = 'Tipos de Ocorrência'

    def quantidade_estudantes(self, obj):
        """Mostra a quantidade de estudantes envolvidos"""
        count = obj.estudantes.count()
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'blue' if count > 0 else 'red',
            f"{count} estudante(s)"
        )

    quantidade_estudantes.short_description = 'Estudantes'

    def save_model(self, request, obj, form, change):
        """Garante que o responsável pelo registro seja definido"""
        if not obj.responsavel_registro_id:
            # Tenta encontrar um servidor associado ao usuário atual
            try:
                servidor = Servidor.objects.get(user=request.user)
                obj.responsavel_registro = servidor
            except Servidor.DoesNotExist:
                # Se não encontrar, usa o primeiro servidor disponível (fallback)
                primeiro_servidor = Servidor.objects.first()
                if primeiro_servidor:
                    obj.responsavel_registro = primeiro_servidor

        # Gera a descrição automaticamente se estiver vazia
        if not obj.descricao and obj.tipos_rapidos.exists():
            tipos_selecionados = obj.tipos_rapidos.all()
            descricoes = [tipo.descricao for tipo in tipos_selecionados]
            obj.descricao = "; ".join(descricoes)

        super().save_model(request, obj, form, change)

    # Ações personalizadas
    actions = ['gerar_recibos_termicos', 'duplicar_ocorrencias']

    def gerar_recibos_termicos(self, request, queryset):
        """Ação para gerar recibos térmicos para ocorrências selecionadas"""
        from .utils import gerar_recibo_termico_ocorrencia_rapida
        from django.core.files.base import ContentFile

        count = 0
        for ocorrencia in queryset:
            try:
                recibo_pdf = gerar_recibo_termico_ocorrencia_rapida(ocorrencia)

                documento = DocumentoGerado.objects.create(
                    ocorrencia_rapida=ocorrencia,
                    tipo_documento='RECIBO_TERMICO',
                    assinado=True
                )

                nome_arquivo = f"recibo_termico_{ocorrencia.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                documento.arquivo.save(nome_arquivo, ContentFile(recibo_pdf.getvalue()))

                if ocorrencia.responsavel_registro:
                    documento.assinaturas.add(ocorrencia.responsavel_registro)

                count += 1
            except Exception as e:
                self.message_user(request, f"Erro ao gerar recibo para ocorrência #{ocorrencia.id}: {str(e)}",
                                  level='ERROR')

        self.message_user(request, f'{count} recibos térmicos gerados com sucesso.')

    gerar_recibos_termicos.short_description = "🖨️ Gerar recibos térmicos para selecionados"

    def duplicar_ocorrencias(self, request, queryset):
        """Duplica as ocorrências rápidas selecionadas"""
        count = 0
        for ocorrencia in queryset:
            try:
                # Cria uma nova ocorrência com os mesmos dados
                nova_ocorrencia = OcorrenciaRapida.objects.create(
                    data=ocorrencia.data,
                    horario=ocorrencia.horario,
                    turma=ocorrencia.turma,
                    descricao=ocorrencia.descricao,
                    responsavel_registro=ocorrencia.responsavel_registro
                )

                # Copia os tipos e estudantes
                nova_ocorrencia.tipos_rapidos.set(ocorrencia.tipos_rapidos.all())
                nova_ocorrencia.estudantes.set(ocorrencia.estudantes.all())

                count += 1
            except Exception as e:
                self.message_user(request, f"Erro ao duplicar ocorrência #{ocorrencia.id}: {str(e)}", level='ERROR')

        self.message_user(request, f'{count} ocorrências duplicadas com sucesso.')

    duplicar_ocorrencias.short_description = "📋 Duplicar ocorrências selecionadas"


# Registrar o novo modelo TipoOcorrenciaRapida
@admin.register(TipoOcorrenciaRapida)
class TipoOcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'ativo', 'quantidade_uso']
    list_filter = ['ativo']
    search_fields = ['codigo', 'descricao']
    list_editable = ['ativo']

    def quantidade_uso(self, obj):
        """Mostra quantas vezes este tipo foi usado"""
        count = obj.ocorrencias_rapidas.count()
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'green' if count > 0 else 'gray',
            f"{count} uso(s)"
        )

    quantidade_uso.short_description = 'Uso'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('ocorrencias_rapidas')


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = [
        'nome',
        'email',
        'celular_formatado',
        'tipo_vinculo',
        'preferencia_contato',
        'total_estudantes_display',
        'estudantes_ativos_display'
    ]

    list_filter = [
        'tipo_vinculo',
        'preferencia_contato',
    ]

    search_fields = [
        'nome',
        'email',
        'celular',
        'estudante__nome',  # Busca através da relação reversa
        'estudante__matricula_sga'
    ]

    # REMOVIDO: filter_horizontal já que não temos mais o campo ManyToMany
    # filter_horizontal = ['estudantes']

    readonly_fields = [
        'total_estudantes_display',
        'estudantes_ativos_display',
        'ultima_atualizacao',
        'info_contato',
        'lista_estudantes'
    ]

    fieldsets = (
        ('Informações Pessoais', {
            'fields': (
                'nome',
                'email',
                'celular',
                'tipo_vinculo'
            )
        }),
        ('Preferências de Contato', {
            'fields': (
                'preferencia_contato',
                'endereco',
                'info_contato'
            ),
            'description': 'Configure como e quando este responsável prefere ser contactado'
        }),
        ('Estudantes Vinculados', {
            'fields': ('lista_estudantes',),
            'description': 'Estudantes vinculados a este responsável (gerenciado através do admin de Estudantes)'
        }),
        ('Estatísticas', {
            'fields': (
                'total_estudantes_display',
                'estudantes_ativos_display'
            ),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('ultima_atualizacao',),
            'classes': ('collapse',)
        }),
    )

    ordering = ['nome']
    list_per_page = 25

    actions = [
        'marcar_preferencia_email',
        'marcar_preferencia_celular',
        'marcar_preferencia_whatsapp',
        'exportar_contatos'
    ]

    # Métodos customizados para display
    def celular_formatado(self, obj):
        """Formata o número de celular para exibição"""
        if obj.celular:
            return format_html('<span style="font-family: monospace;">{}</span>', obj.celular)
        return "-"

    celular_formatado.short_description = 'Celular'

    def total_estudantes_display(self, obj):
        """Retorna o total de estudantes vinculados"""
        count = obj.total_estudantes
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )

    total_estudantes_display.short_description = '📚 Total Estudantes'

    def estudantes_ativos_display(self, obj):
        """Mostra quantos estudantes estão ativos"""
        ativos = obj.estudantes_ativos.count()
        total = obj.total_estudantes
        color = "green" if ativos == total else "orange" if ativos > 0 else "red"
        return format_html(
            '<span style="font-weight: bold; color: {};">{}/{} ativos</span>',
            color, ativos, total
        )

    estudantes_ativos_display.short_description = '✅ Estudantes Ativos'

    def info_contato(self, obj):
        """Informações de contato formatadas"""
        info = []
        if obj.email:
            info.append(f"📧 {obj.email}")
        if obj.celular:
            info.append(f"📱 {obj.celular}")
        if obj.endereco:
            info.append(f"🏠 {obj.endereco[:50]}...")

        if not info:
            return "Nenhuma informação de contato disponível"

        return format_html("<br>".join(info))

    info_contato.short_description = 'Informações de Contato'

    def lista_estudantes(self, obj):
        """Lista os estudantes vinculados"""
        estudantes = obj.estudantes.all()
        if not estudantes:
            return "Nenhum estudante vinculado"

        lista = []
        for estudante in estudantes:
            status = "✅" if estudante.situacao == 'ATIVO' else "❌"
            lista.append(f"{status} {estudante.nome} ({estudante.matricula_sga}) - {estudante.get_situacao_display()}")

        return format_html("<br>".join(lista))

    lista_estudantes.short_description = 'Estudantes Vinculados'

    def get_queryset(self, request):
        """Otimiza as queries para a listagem"""
        return super().get_queryset(request).prefetch_related('estudantes')

    # Actions personalizadas
    def marcar_preferencia_email(self, request, queryset):
        updated = queryset.update(preferencia_contato='EMAIL')
        self.message_user(request, f'{updated} responsável(eis) marcado(s) com preferência por Email.')

    marcar_preferencia_email.short_description = "🗳️ Definir preferência: Email"

    def marcar_preferencia_celular(self, request, queryset):
        updated = queryset.update(preferencia_contato='CELULAR')
        self.message_user(request, f'{updated} responsável(eis) marcado(s) com preferência por Celular.')

    marcar_preferencia_celular.short_description = "📱 Definir preferência: Celular"

    def marcar_preferencia_whatsapp(self, request, queryset):
        updated = queryset.update(preferencia_contato='WHATSAPP')
        self.message_user(request, f'{updated} responsável(eis) marcado(s) com preferência por WhatsApp.')

    marcar_preferencia_whatsapp.short_description = "💚 Definir preferência: WhatsApp"

    def exportar_contatos(self, request, queryset):
        self.message_user(request,
                          f'Exportação de {queryset.count()} contatos preparada. Esta funcionalidade será implementada em breve.')

    exportar_contatos.short_description = "📤 Exportar contatos selecionados"


# Inline para mostrar responsáveis no admin de Estudante
class ResponsavelInline(admin.TabularInline):
    model = Estudante.responsaveis.through
    extra = 1
    verbose_name = "Responsável"
    verbose_name_plural = "Responsáveis"
    autocomplete_fields = ['responsavel']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "responsavel":
            kwargs["queryset"] = Responsavel.objects.all().order_by('nome')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Atualizar o admin de Estudante
@admin.register(Estudante)
class EstudanteAdmin(admin.ModelAdmin):
    list_display = [
        'matricula_sga',
        'nome',
        'turma',
        'situacao',
        'tem_foto',
        'total_responsaveis_display'
    ]

    list_filter = [
        'situacao',
        'campus',
        'curso',
        'turma',
        'responsaveis__tipo_vinculo'
    ]

    search_fields = [
        'nome',
        'matricula_sga',
        'email',
        'responsaveis__nome'
    ]

    inlines = [ResponsavelInline]
    filter_horizontal = ['responsaveis']

    readonly_fields = ['total_responsaveis_display']

    fieldsets = (
        ('Identificação', {
            'fields': ('matricula_sga', 'nome', 'cpf', 'data_nascimento')
        }),
        ('Foto de Perfil', {
            'fields': ('foto', 'foto_url'),
            'description': 'Use foto_url para links do Google Drive. Formato: https://drive.google.com/uc?export=view&id=ID_DA_IMAGEM'
        }),
        ('Contatos', {
            'fields': ('email',)
        }),
        ('Endereço', {
            'fields': ('logradouro', 'bairro_cidade', 'uf'),
            'classes': ('collapse',)
        }),
        ('Acadêmico', {
            'fields': ('campus', 'curso', 'turma', 'turma_periodo', 'situacao', 'data_ingresso')
        }),
        ('Responsáveis', {
            'fields': ('responsaveis', 'total_responsaveis_display'),
            'description': 'Responsáveis vinculados a este estudante'
        }),
    )

    def total_responsaveis_display(self, obj):
        """Retorna o total de responsáveis vinculados"""
        count = obj.responsaveis.count()
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'green' if count > 0 else 'orange',
            f"{count} responsável(eis)"
        )

    total_responsaveis_display.short_description = 'Total de Responsáveis'

    def tem_foto(self, obj):
        if obj.get_foto_url():
            return '✅ Sim'
        return '❌ Não'

    tem_foto.short_description = 'Foto'

    def get_queryset(self, request):
        """Otimiza as queries para a listagem"""
        return super().get_queryset(request).prefetch_related('responsaveis')

# Mantenha os outros registros admin existentes...
@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ['nome', 'sigla', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'sigla']


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'campus', 'codigo', 'ativo']
    list_filter = ['campus', 'ativo']
    search_fields = ['nome', 'codigo']


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'curso', 'ano', 'semestre', 'ativa']
    list_filter = ['ano', 'semestre', 'ativa', 'curso__campus']
    search_fields = ['nome']

# ... (mantenha os outros admin registrations existentes)