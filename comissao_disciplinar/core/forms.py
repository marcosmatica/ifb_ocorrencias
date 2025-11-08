from django import forms
from django.forms import modelformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import (
    Ocorrencia, Estudante, Responsavel, NotificacaoOficial,
    Recurso, ComissaoProcessoDisciplinar, DocumentoGerado, Curso, Turma, Infracao,
    Servidor
)


class OcorrenciaForm(forms.ModelForm):
    # Campo de busca para filtrar estudantes (NÃO incluído nos fields do Meta)
    busca_estudante = forms.CharField(
        required=False,
        label="Buscar estudante",
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o nome ou matrícula do estudante...',
            'class': 'form-control',
            'id': 'busca-estudante'
        })
    )
    
    # Campo de filtro por turma (NÃO incluído nos fields do Meta)
    turma_filtro = forms.ModelChoiceField(
        queryset=Turma.objects.all().distinct(),
        required=False,
        label="Filtrar estudantes por turma",
        empty_label="Todas as turmas",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'turma-filtro'
        })
    )

    class Meta:
        model = Ocorrencia
        fields = [
            'data', 'horario', 'curso', 'turma', 'estudantes',
            'descricao', 'infracao', 'testemunhas', 'evidencias',
            'medida_preventiva'
        ]
        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input',
                'id': 'id_data'
            }),
            'horario': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control modern-time-input',
                'id': 'id_horario'
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Descreva detalhadamente o ocorrido...'
            }),
            'testemunhas': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Nome das testemunhas, separadas por vírgula'
            }),
            'medida_preventiva': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Descreva as medidas imediatas tomadas...'
            }),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'turma': forms.Select(attrs={'class': 'form-control', 'id': 'id_turma'}),
            'infracao': forms.Select(attrs={'class': 'form-control'}),
            'evidencias': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)

        # Ordenar estudantes por nome
        self.fields['estudantes'].queryset = Estudante.objects.all().order_by('nome')
        
        # Remover o widget padrão de checkbox para usar customizado
        self.fields['estudantes'].widget = forms.CheckboxSelectMultiple(attrs={
            'class': 'estudante-checkbox'
        })

        # Se foi enviado um filtro de turma, aplicar
        if 'turma_filtro' in self.data and self.data['turma_filtro']:
            try:
                turma_id = int(self.data['turma_filtro'])
                self.fields['estudantes'].queryset = Estudante.objects.filter(
                    turma_id=turma_id
                ).order_by('nome')
            except (ValueError, TypeError):
                pass

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Registrar Ocorrência', css_class='btn-primary'))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.servidor:
            instance.responsavel_registro = self.servidor
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class OcorrenciaRapidaForm(forms.ModelForm):
    """Formulário simplificado para ocorrências simples/frequentes"""
    TIPOS_RAPIDOS = [
        ('ATRASO', 'Atraso'),
        ('CELULAR', 'Uso indevido de celular'),
        ('UNIFORME', 'Sem uniforme'),
        ('RECUSA', 'Recusa a participar das atividades'),
        ('AUSENCIA', 'Ausência de sala'),
        ('SAIDA', 'Saída Antecipada')
    ]

    tipo_rapido = forms.ChoiceField(
        choices=TIPOS_RAPIDOS,
        label='Tipo de Ocorrência',
        widget=forms.RadioSelect(attrs={'class': 'tipo-rapido-radio'})
    )
    
    # Campo de busca para estudantes
    busca_estudante = forms.CharField(
        required=False,
        label="Buscar estudante",
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o nome ou matrícula...',
            'class': 'form-control',
            'id': 'busca-estudante-rapido'
        })
    )

    class Meta:
        model = Ocorrencia
        fields = ['data', 'horario', 'turma', 'estudantes', 'tipo_rapido']
        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input'
            }),
            'horario': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control modern-time-input'
            }),
            'turma': forms.Select(attrs={
                'class': 'form-control',
                'id': 'turma-filtro-rapido'
            }),
            'estudantes': forms.CheckboxSelectMultiple(attrs={
                'class': 'estudante-checkbox'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)
        
        # Ordenar estudantes
        self.fields['estudantes'].queryset = Estudante.objects.all().order_by('nome')
        self.helper = FormHelper()
        self.helper.form_method = 'post'


class DefesaForm(forms.Form):
    defesa_texto = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
        label='Argumentação de Defesa',
        required=True
    )
    defesa_arquivo = forms.FileField(
        label='Anexar Documento (opcional)',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = ['argumentacao', 'documentos_anexos']
        widgets = {
            'argumentacao': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'documentos_anexos': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Protocolar Recurso'))


class ComissaoForm(forms.ModelForm):
    class Meta:
        model = ComissaoProcessoDisciplinar
        fields = ['presidente', 'membros']
        widgets = {
            'presidente': forms.Select(attrs={'class': 'form-control'}),
            'membros': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas servidores membros da comissão disciplinar
        self.fields['presidente'].queryset = Servidor.objects.filter(membro_comissao_disciplinar=True)
        self.fields['membros'].queryset = Servidor.objects.filter(membro_comissao_disciplinar=True)


class NotificacaoForm(forms.ModelForm):
    class Meta:
        model = NotificacaoOficial
        fields = ['tipo', 'meio_envio', 'destinatarios', 'texto']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'meio_envio': forms.Select(attrs={'class': 'form-control'}),
            'destinatarios': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'texto': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }


class FiltroOcorrenciaForm(forms.Form):
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos')] + Ocorrencia.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    curso = forms.ModelChoiceField(
        queryset=Curso.objects.all().distinct(),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.all().distinct(),
        required=False,
        empty_label="Todas",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    gravidade = forms.ChoiceField(
        choices=[('', 'Todas')] + Infracao.GRAVIDADE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class EstudanteForm(forms.ModelForm):
    class Meta:
        model = Estudante
        fields = [
            'matricula_sga', 'nome', 'cpf', 'data_nascimento',
            'email', 'email_responsavel', 'contato_responsavel',
            'logradouro', 'bairro_cidade', 'uf',
            'turma', 'turma_periodo', 'campus', 'curso',
            'situacao', 'data_ingresso', 'foto', 'responsavel'
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_ingresso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
        }


class ResponsavelForm(forms.ModelForm):
    class Meta:
        model = Responsavel
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tipo_vinculo': forms.Select(attrs={'class': 'form-control'}),
            'preferencia_contato': forms.Select(attrs={'class': 'form-control'}),
        }