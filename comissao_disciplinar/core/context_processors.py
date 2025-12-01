# Criar arquivo: comissao_disciplinar/core/context_processors.py

from datetime import datetime
from django.utils import timezone
from .models import AlertaLimiteOcorrenciaRapida


def alertas_ativos(request):
    """
    Adiciona contagem de alertas ativos ao contexto global
    """
    if request.user.is_authenticated and hasattr(request.user, 'servidor'):
        # Alertas do mês atual
        hoje = timezone.now().date()
        primeiro_dia_mes = hoje.replace(day=1)

        alertas_count = AlertaLimiteOcorrenciaRapida.objects.filter(
            mes_referencia=primeiro_dia_mes
        ).count()

        return {
            'alertas_ativos_count': alertas_count
        }

    return {
        'alertas_ativos_count': 0
    }

# Adicionar em settings.py:
# TEMPLATES = [
#     {
#         ...
#         'OPTIONS': {
#             'context_processors': [
#                 ...
#                 'core.context_processors.alertas_ativos',
#             ],
#         },
#     },
# ]