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
    turma_filtro = forms.ModelChoiceField(
        queryset=Turma.objects.all(),
        required=False,
        label="Filtrar estudantes por turma",
        empty_label="Selecione uma turma para filtrar"
    )

    class Meta:
        model = Ocorrencia
        fields = [
            'data', 'horario', 'curso', 'turma', 'estudantes',
            'descricao', 'infracao', 'testemunhas', 'evidencias',
            'medida_preventiva'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'horario': forms.TimeInput(attrs={'type': 'time'}),
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'testemunhas': forms.Textarea(attrs={'rows': 2}),
            'medida_preventiva': forms.Textarea(attrs={'rows': 3}),
            'estudantes': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)

        # Ordenar estudantes por nome
        self.fields['estudantes'].queryset = Estudante.objects.all().order_by('nome')

        # Se foi enviado um filtro de turma, aplicar
        if 'turma_filtro' in self.data and self.data['turma_filtro']:
            try:
                turma_id = int(self.data['turma_filtro'])
                self.fields['estudantes'].queryset = Estudante.objects.filter(
                    turma_id=turma_id
                ).order_by('nome')
            except (ValueError, TypeError):
                pass  # Manter todos os estudantes se o filtro for inválido

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
    ]

    tipo_rapido = forms.ChoiceField(choices=TIPOS_RAPIDOS, label='Tipo de Ocorrência')

    class Meta:
        model = Ocorrencia
        fields = ['data', 'horario', 'turma', 'estudantes', 'tipo_rapido']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'horario': forms.TimeInput(attrs={'type': 'time'}),
            'estudantes': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'


class DefesaForm(forms.Form):
    defesa_texto = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        label='Argumentação de Defesa',
        required=True
    )
    defesa_arquivo = forms.FileField(
        label='Anexar Documento (opcional)',
        required=False
    )


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = ['argumentacao', 'documentos_anexos']
        widgets = {
            'argumentacao': forms.Textarea(attrs={'rows': 6}),
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
            'destinatarios': forms.Textarea(attrs={'rows': 2}),
            'texto': forms.Textarea(attrs={'rows': 5}),
        }


class FiltroOcorrenciaForm(forms.Form):
    data_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    status = forms.ChoiceField(choices=[('', 'Todos')] + Ocorrencia.STATUS_CHOICES, required=False)
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), required=False, empty_label="Todos")
    turma = forms.ModelChoiceField(queryset=Turma.objects.all(), required=False, empty_label="Todas")
    gravidade = forms.ChoiceField(
        choices=[('', 'Todas')] + Infracao.GRAVIDADE_CHOICES,
        required=False
    )


class EstudanteForm(forms.ModelForm):
    class Meta:
        model = Estudante
        fields = [
            'matricula_sga', 'nome', 'email', 'turma', 'campus',
            'curso', 'responsavel', 'situacao', 'data_ingresso', 'foto'
        ]
        widgets = {
            'data_ingresso': forms.DateInput(attrs={'type': 'date'}),
        }


class ResponsavelForm(forms.ModelForm):
    class Meta:
        model = Responsavel
        fields = '__all__'
        widgets = {
            'endereco': forms.Textarea(attrs={'rows': 3}),
        }