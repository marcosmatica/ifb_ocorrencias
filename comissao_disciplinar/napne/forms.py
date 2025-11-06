from django import forms
from .models import (
    FichaEstudanteNAPNE, AtendimentoNAPNE, ObservacaoEncaminhamento,
    TipoAtendimentoNAPNE, StatusAtendimentoNAPNE
)
from core.models import Estudante, Turma

class FichaEstudanteNAPNEForm(forms.ModelForm):
    class Meta:
        model = FichaEstudanteNAPNE
        fields = [
            'estudante', 'turma', 'necessidade_especifica', 'telefone',
            'atendido_por', 'laudo_apresentado', 'observacao_laudo_atual',
            'desempenho_1bim', 'desempenho_2bim', 'desempenho_3bim',
            'desempenho_4bim', 'resultado_final'
        ]
        widgets = {
            'estudante': forms.Select(attrs={'class': 'form-control'}),
            'turma': forms.Select(attrs={'class': 'form-control'}),
            'necessidade_especifica': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'atendido_por': forms.Select(attrs={'class': 'form-control'}),
            'observacao_laudo_atual': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'desempenho_1bim': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'desempenho_2bim': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'desempenho_3bim': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'desempenho_4bim': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'resultado_final': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class AtendimentoNAPNEForm(forms.ModelForm):
    # Campos de busca (não salvos)
    busca_estudante = forms.CharField(
        required=False,
        label="Buscar estudante",
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o nome ou matrícula...',
            'class': 'form-control',
            'id': 'busca-estudante-napne'
        })
    )
    
    turma_filtro = forms.ModelChoiceField(
        queryset=Turma.objects.all(),
        required=False,
        label="Filtrar por turma",
        empty_label="Todas as turmas",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'turma-filtro-napne'})
    )
    
    class Meta:
        model = AtendimentoNAPNE
        fields = [
            'estudante', 'turma', 'origem', 'data', 'tipo_atendimento',
            'laudo_previo', 'necessidades_especificas', 'detalhamento',
            'acoes', 'resumo_atendimento', 'publicar_ficha_aluno', 'status'
        ]
        widgets = {
            'estudante': forms.Select(attrs={'class': 'form-control'}),
            'turma': forms.Select(attrs={'class': 'form-control'}),
            'origem': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_atendimento': forms.Select(attrs={'class': 'form-control'}),
            'laudo_previo': forms.Select(attrs={'class': 'form-control'}),
            'necessidades_especificas': forms.CheckboxSelectMultiple(attrs={'class': 'necessidade-checkbox'}),
            'detalhamento': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'acoes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'resumo_atendimento': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)
        
        # Ordenar estudantes
        self.fields['estudante'].queryset = Estudante.objects.filter(
            situacao='ATIVO'
        ).order_by('nome')


class ObservacaoEncaminhamentoForm(forms.ModelForm):
    class Meta:
        model = ObservacaoEncaminhamento
        fields = ['setor', 'observacao']
        widgets = {
            'setor': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }