from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import path
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
        'listar_tipos',
        'quantidade_estudantes',
        'responsavel_registro'
    ]
    list_filter = [
        'data',
        'turma__curso__campus',
        'tipos_rapidos'
    ]
    search_fields = [
        'estudantes__nome',
        'estudantes__matricula_sga',
        'descricao',
        'tipos_rapidos__codigo',
        'tipos_rapidos__descricao'
    ]
    date_hierarchy = 'data'
    filter_horizontal = ['tipos_rapidos', 'estudantes']

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
        tipos = obj.tipos_rapidos.all()
        if tipos:
            return ", ".join([tipo.codigo for tipo in tipos])
        return "Nenhum tipo"

    listar_tipos.short_description = 'Tipos de Ocorrência'

    def quantidade_estudantes(self, obj):
        count = obj.estudantes.count()
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'blue' if count > 0 else 'red',
            f"{count} estudante(s)"
        )

    quantidade_estudantes.short_description = 'Estudantes'

    def save_model(self, request, obj, form, change):
        if not obj.responsavel_registro_id:
            try:
                servidor = Servidor.objects.get(user=request.user)
                obj.responsavel_registro = servidor
            except Servidor.DoesNotExist:
                primeiro_servidor = Servidor.objects.first()
                if primeiro_servidor:
                    obj.responsavel_registro = primeiro_servidor

        if not obj.descricao and obj.tipos_rapidos.exists():
            tipos_selecionados = obj.tipos_rapidos.all()
            descricoes = [tipo.descricao for tipo in tipos_selecionados]
            obj.descricao = "; ".join(descricoes)

        super().save_model(request, obj, form, change)

    actions = ['gerar_recibos_termicos', 'duplicar_ocorrencias']

    def gerar_recibos_termicos(self, request, queryset):
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
        count = 0
        for ocorrencia in queryset:
            try:
                nova_ocorrencia = OcorrenciaRapida.objects.create(
                    data=ocorrencia.data,
                    horario=ocorrencia.horario,
                    turma=ocorrencia.turma,
                    descricao=ocorrencia.descricao,
                    responsavel_registro=ocorrencia.responsavel_registro
                )

                nova_ocorrencia.tipos_rapidos.set(ocorrencia.tipos_rapidos.all())
                nova_ocorrencia.estudantes.set(ocorrencia.estudantes.all())

                count += 1
            except Exception as e:
                self.message_user(request, f"Erro ao duplicar ocorrência #{ocorrencia.id}: {str(e)}", level='ERROR')

        self.message_user(request, f'{count} ocorrência(s) duplicada(s) com sucesso.')

    duplicar_ocorrencias.short_description = "📋 Duplicar ocorrências selecionadas"


@admin.register(TipoOcorrenciaRapida)
class TipoOcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao_resumida', 'ativo']
    list_filter = ['ativo']
    search_fields = ['codigo', 'descricao']

    def descricao_resumida(self, obj):
        if len(obj.descricao) > 80:
            return obj.descricao[:80] + '...'
        return obj.descricao

    descricao_resumida.short_description = 'Descrição'


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_vinculo', 'email', 'celular', 'total_estudantes_display']
    list_filter = ['tipo_vinculo', 'preferencia_contato']
    search_fields = ['nome', 'email', 'celular']
    #filter_horizontal = ['estudantes']

    readonly_fields = ['total_estudantes_display', 'estudantes_ativos_display', 'ultima_atualizacao']

    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'tipo_vinculo', 'endereco')
        }),
        ('Contatos', {
            'fields': ('email', 'celular', 'preferencia_contato')
        }),
        ('Estudantes Vinculados', {
            'fields': ('estudantes', 'total_estudantes_display', 'estudantes_ativos_display'),
            'description': 'Estudantes vinculados a este responsável'
        }),
        ('Informações do Sistema', {
            'fields': ('ultima_atualizacao',),
            'classes': ('collapse',)
        }),
    )

    def total_estudantes_display(self, obj):
        count = obj.total_estudantes
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'green' if count > 0 else 'orange',
            f"{count} estudante(s)"
        )

    total_estudantes_display.short_description = 'Total de Estudantes'

    def estudantes_ativos_display(self, obj):
        count = obj.estudantes_ativos.count()
        total = obj.total_estudantes
        return format_html(
            '<span style="font-weight: bold; color: green;">{}/{}</span> ativos',
            count, total
        )

    estudantes_ativos_display.short_description = 'Estudantes Ativos'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('estudantes')


@admin.register(Estudante)
class EstudanteAdmin(admin.ModelAdmin):
    list_display = ['matricula_sga', 'nome', 'situacao_formatada', 'turma', 'curso', 'campus', 'tem_foto']
    list_filter = ['situacao', 'campus', 'curso', 'turma']
    search_fields = ['nome', 'matricula_sga', 'cpf', 'email']
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

    # AÇÕES CUSTOMIZADAS PARA ALTERAR SITUAÇÃO
    actions = [
        'marcar_como_ativo',
        'marcar_como_inativo',
        'marcar_como_trancado',
        'marcar_como_evadido',
        'marcar_como_formado',
        'marcar_como_transferido',
        'alterar_situacao_personalizada',
    ]

    def situacao_formatada(self, obj):
        """Exibe a situação com cores"""
        cores = {
            'ATIVO': 'green',
            'INATIVO': 'gray',
            'TRANCADO': 'orange',
            'EVADIDO': 'red',
            'FORMADO': 'blue',
            'TRANSFERIDO': 'purple',
        }
        cor = cores.get(obj.situacao, 'black')
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            cor,
            obj.get_situacao_display()
        )

    situacao_formatada.short_description = 'Situação'
    situacao_formatada.admin_order_field = 'situacao'

    def total_responsaveis_display(self, obj):
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
        return super().get_queryset(request).prefetch_related('responsaveis')

    # AÇÕES PARA ALTERAR SITUAÇÃO
    def marcar_como_ativo(self, request, queryset):
        """Marca os estudantes selecionados como ATIVO"""
        updated = queryset.update(situacao='ATIVO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como ATIVO.')

    marcar_como_ativo.short_description = "✅ Marcar como ATIVO"

    def marcar_como_inativo(self, request, queryset):
        """Marca os estudantes selecionados como INATIVO"""
        updated = queryset.update(situacao='INATIVO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como INATIVO.')

    marcar_como_inativo.short_description = "⚫ Marcar como INATIVO"

    def marcar_como_trancado(self, request, queryset):
        """Marca os estudantes selecionados como TRANCADO"""
        updated = queryset.update(situacao='TRANCADO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como TRANCADO.')

    marcar_como_trancado.short_description = "🔶 Marcar como TRANCADO"

    def marcar_como_evadido(self, request, queryset):
        """Marca os estudantes selecionados como EVADIDO"""
        updated = queryset.update(situacao='EVADIDO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como EVADIDO.')

    marcar_como_evadido.short_description = "❌ Marcar como EVADIDO"

    def marcar_como_formado(self, request, queryset):
        """Marca os estudantes selecionados como FORMADO"""
        updated = queryset.update(situacao='FORMADO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como FORMADO.')

    marcar_como_formado.short_description = "🎓 Marcar como FORMADO"

    def marcar_como_transferido(self, request, queryset):
        """Marca os estudantes selecionados como TRANSFERIDO"""
        updated = queryset.update(situacao='TRANSFERIDO')
        self.message_user(request, f'{updated} estudante(s) marcado(s) como TRANSFERIDO.')

    marcar_como_transferido.short_description = "🔄 Marcar como TRANSFERIDO"

    def alterar_situacao_personalizada(self, request, queryset):
        """
        Permite selecionar a situação desejada através de uma página intermediária
        """
        # Salva os IDs dos estudantes selecionados na sessão
        request.session['estudantes_ids'] = list(queryset.values_list('id', flat=True))
        
        # Se o formulário foi submetido
        if 'aplicar' in request.POST:
            nova_situacao = request.POST.get('nova_situacao')
            estudantes_ids = request.session.get('estudantes_ids', [])
            
            if nova_situacao and estudantes_ids:
                updated = Estudante.objects.filter(id__in=estudantes_ids).update(situacao=nova_situacao)
                self.message_user(
                    request,
                    f'{updated} estudante(s) alterado(s) para {dict(Estudante.SITUACAO_CHOICES)[nova_situacao]}.'
                )
                # Limpa a sessão
                del request.session['estudantes_ids']
                return HttpResponseRedirect(request.get_full_path())
        
        # Template HTML inline para o formulário intermediário
        from django.template.response import TemplateResponse
        
        context = {
            'estudantes': queryset,
            'situacao_choices': Estudante.SITUACAO_CHOICES,
            'opts': self.model._meta,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
        }
        
        return TemplateResponse(
            request,
            'admin/estudantes/alterar_situacao.html',
            context
        )

    alterar_situacao_personalizada.short_description = "🔧 Alterar situação (escolher)"


# Registro dos outros modelos
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


@admin.register(ConfiguracaoLimiteOcorrenciaRapida)
class ConfiguracaoLimiteOcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = [
        'tipo_ocorrencia',
        'limite_mensal',
        'coordenacoes_notificar',
        'gerar_notificacao_sistema',
        'gerar_email_responsaveis',
        'ativo',
        'get_email_coordenacao_icone'
    ]

    list_filter = ['ativo', 'coordenacoes_notificar', 'gerar_email_coordenacao']

    search_fields = ['tipo_ocorrencia__codigo', 'tipo_ocorrencia__descricao']

    fieldsets = (
        ('Tipo de Ocorrência e Limite', {
            'fields': ('tipo_ocorrencia', 'limite_mensal', 'ativo')
        }),
        ('Notificações no Sistema', {
            'fields': ('gerar_notificacao_sistema',)
        }),
        ('Notificações por E-mail', {
            'fields': (
                'gerar_email_coordenacao',
                'coordenacoes_notificar',
                'gerar_email_responsaveis'
            ),
            'description': 'Emails serão enviados mensalmente se o limite for atingido.'
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tipo_ocorrencia')

    actions = ['duplicar_configuracao', 'ativar_configuracoes', 'desativar_configuracoes']

    def get_email_coordenacao_icone(self, obj):
        if obj.gerar_email_coordenacao:
            return format_html('<span style="color: green; font-weight: bold;">✔</span>')
        return format_html('<span style="color: red; font-weight: bold;">✘</span>')

    get_email_coordenacao_icone.short_description = 'E-mail Coord.'
    get_email_coordenacao_icone.admin_order_field = 'gerar_email_coordenacao'

    def duplicar_configuracao(self, request, queryset):
        count = 0
        for config in queryset:
            nova_config = ConfiguracaoLimiteOcorrenciaRapida.objects.create(
                tipo_ocorrencia=config.tipo_ocorrencia,
                limite_mensal=config.limite_mensal,
                coordenacoes_notificar=config.coordenacoes_notificar,
                gerar_notificacao_sistema=config.gerar_notificacao_sistema,
                gerar_email_coordenacao=config.gerar_email_coordenacao,
                gerar_email_responsaveis=config.gerar_email_responsaveis,
                ativo=False
            )
            count += 1

        self.message_user(request, f'{count} configuração(ões) duplicada(s) com sucesso. Criadas como inativas.')

    duplicar_configuracao.short_description = "📋 Duplicar configurações selecionadas"

    def ativar_configuracoes(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(request, f'{updated} configuração(ões) ativada(s).')

    ativar_configuracoes.short_description = "✅ Ativar configurações selecionadas"

    def desativar_configuracoes(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, f'{updated} configuração(ões) desativada(s).')

    desativar_configuracoes.short_description = "❌ Desativar configurações selecionadas"


@admin.register(AlertaLimiteOcorrenciaRapida)
class AlertaLimiteOcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = [
        'estudante',
        'tipo_ocorrencia',
        'quantidade_ocorrencias',
        'limite_configurado',
        'mes_referencia',
        'notificacao_sistema_criada',
        'email_coordenacao_enviado',
        'email_responsaveis_enviado',
        'criado_em'
    ]

    list_filter = [
        'mes_referencia',
        'tipo_ocorrencia',
        'notificacao_sistema_criada',
        'email_coordenacao_enviado',
        'email_responsaveis_enviado',
        'criado_em'
    ]

    search_fields = [
        'estudante__nome',
        'estudante__matricula_sga',
        'tipo_ocorrencia__codigo'
    ]

    readonly_fields = [
        'estudante',
        'tipo_ocorrencia',
        'configuracao',
        'limite_configurado',
        'mes_referencia',
        'quantidade_ocorrencias',
        'notificacao_sistema_criada',
        'email_coordenacao_enviado',
        'email_responsaveis_enviado',
        'criado_em'
    ]

    date_hierarchy = 'criado_em'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'estudante', 'tipo_ocorrencia', 'configuracao'
        )

    def limite_configurado(self, obj):
        if obj.configuracao:
            return format_html(
                '<span style="font-weight: bold; color: orange;">{}</span>',
                obj.configuracao.limite_mensal
            )
        return 'N/A'

    limite_configurado.short_description = 'Limite'
    limite_configurado.admin_order_field = 'configuracao__limite_mensal'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser