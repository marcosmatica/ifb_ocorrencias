from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, modelformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Projeto, ParticipacaoServidor, ParticipacaoEstudante
from core.models import Servidor, Estudante


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            'numero_processo', 'titulo', 'tipo', 'data_inicio', 'data_final',
            'tema', 'area', 'coordenador', 'envolve_estudantes',
            'situacao', 'observacoes', 'periodicidade_relatorio'
        ]
        widgets = {
            'numero_processo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 23127.000123/2024-45'
            }),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título do projeto'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input'
            }),
            'data_final': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input'
            }),
            'tema': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tema principal do projeto'
            }),
            'area': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Área do conhecimento'
            }),
            'coordenador': forms.Select(attrs={'class': 'form-control'}),
            'envolve_estudantes': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'situacao': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observações gerais sobre o projeto'
            }),
            'periodicidade_relatorio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12
            }),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)

        # Filtrar apenas servidores ativos
        self.fields['coordenador'].queryset = Servidor.objects.filter(
            user__is_active=True
        ).order_by('nome')

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Salvar Projeto', css_class='btn-primary'))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.servidor and not instance.criado_por:
            instance.criado_por = self.servidor
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ParticipacaoServidorForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoServidor
        fields = ['servidor', 'semestre', 'horas_semanais']
        widgets = {
            'servidor': forms.Select(attrs={'class': 'form-control'}),
            'semestre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2024.1',
                'pattern': r'\d{4}\.[12]'
            }),
            'horas_semanais': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.5,
                'max': 12,
                'step': 0.5
            }),
        }

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        super().__init__(*args, **kwargs)

        # Filtrar servidores (excluir coordenador do projeto)
        queryset = Servidor.objects.filter(user__is_active=True).order_by('nome')
        if self.projeto:
            queryset = queryset.exclude(id=self.projeto.coordenador.id)
        self.fields['servidor'].queryset = queryset

        # Pré-preencher semestre atual
        if not self.instance.pk:
            self.fields['semestre'].initial = Projeto.get_semestre_atual()

    def clean(self):
        cleaned_data = super().clean()
        servidor = cleaned_data.get('servidor')
        semestre = cleaned_data.get('semestre')
        horas_semanais = cleaned_data.get('horas_semanais')

        if servidor and semestre and horas_semanais:
            # Verificar se não é o coordenador
            if self.projeto and servidor == self.projeto.coordenador:
                raise ValidationError('O coordenador não pode ser também participante.')

            # Verificar total de horas
            total = ParticipacaoServidor.objects.filter(
                servidor=servidor,
                semestre=semestre
            ).exclude(pk=self.instance.pk).aggregate(
                total=models.Sum('horas_semanais')
            )['total'] or 0

            if total + float(horas_semanais) > 12:
                raise ValidationError(
                    f'{servidor.nome} já possui {total}h/semana em outros projetos. '
                    f'Total não pode exceder 12h semanais.'
                )

        return cleaned_data


class ParticipacaoEstudanteForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoEstudante
        fields = [
            'estudante', 'bolsista', 'valor_bolsa',
            'data_inicio', 'data_fim', 'ativo'
        ]
        widgets = {
            'estudante': forms.Select(attrs={'class': 'form-control'}),
            'bolsista': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'valor_bolsa': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.01
            }),
            'data_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input'
            }),
            'data_fim': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control modern-date-input'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar apenas estudantes ativos
        self.fields['estudante'].queryset = Estudante.objects.filter(
            situacao='ATIVO'
        ).order_by('nome')


class FiltroProjetoForm(forms.Form):
    situacao = forms.ChoiceField(
        choices=[('', 'Todas')] + Projeto.SITUACAO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo = forms.ChoiceField(
        choices=[('', 'Todos')] + Projeto.TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    coordenador = forms.ModelChoiceField(
        queryset=Servidor.objects.filter(user__is_active=True).order_by('nome'),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    ano = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ano'
        })
    )
    relatorio_atrasado = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class RelatorioEntregueForm(forms.Form):
    data_entrega = forms.DateField(
        label='Data de entrega do relatório',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control modern-date-input'
        })
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observações sobre o relatório (opcional)'
        })
    )


class DefinirProximoRelatorioForm(forms.Form):
    """Formulário para coord. pesquisa/extensão definir manualmente próximo relatório"""
    proximo_relatorio = forms.DateField(
        label='Próxima data de entrega',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control modern-date-input'
        })
    )
    motivo = forms.CharField(
        label='Motivo da alteração',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Explique o motivo da alteração manual da data'
        })
    )


# Formsets para edição em lote
ParticipacaoServidorFormSet = inlineformset_factory(
    Projeto,
    ParticipacaoServidor,
    form=ParticipacaoServidorForm,
    extra=1,
    can_delete=True,
    fields=['servidor', 'semestre', 'horas_semanais']
)

ParticipacaoEstudanteFormSet = inlineformset_factory(
    Projeto,
    ParticipacaoEstudante,
    form=ParticipacaoEstudanteForm,
    extra=1,
    can_delete=True,
    fields=['estudante', 'bolsista', 'valor_bolsa', 'data_inicio', 'data_fim', 'ativo']
)