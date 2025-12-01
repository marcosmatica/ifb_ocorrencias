from django.utils import timezone
from django.db.models import Count, Q
from .models import (
    OcorrenciaRapida,
    ConfiguracaoLimiteOcorrenciaRapida,
    AlertaLimiteOcorrenciaRapida,
    Estudante
)
import logging

logger = logging.getLogger(__name__)


def verificar_limites_ocorrencia(ocorrencia):
    """
    Verifica se uma ocorrência específica dispara algum alerta.
    Usado em signals ou no save_model.
    """
    estudantes = ocorrencia.estudantes.all()
    tipos = ocorrencia.tipos_rapidos.all()

    # Data da ocorrência define o mês de referência
    mes_referencia = ocorrencia.data.strftime('%Y-%m')

    # Filtra configurações ativas para os tipos desta ocorrência
    configs = ConfiguracaoLimiteOcorrenciaRapida.objects.filter(
        tipo_ocorrencia__in=tipos,
        ativo=True
    ).select_related('tipo_ocorrencia')

    for config in configs:
        for estudante in estudantes:
            processar_alerta_individual(estudante, config, mes_referencia)


def processar_alerta_individual(estudante, config, mes_referencia):
    """
    Lógica isolada para verificar e criar/atualizar alerta para um estudante/config específico.
    """
    ano, mes = map(int, mes_referencia.split('-'))

    # CORREÇÃO AQUI: Uso de 'ocorrencias_rapidas' em vez de 'ocorrenciarapida'
    total_ocorrencias = OcorrenciaRapida.objects.filter(
        estudantes=estudante,
        tipos_rapidos=config.tipo_ocorrencia,
        data__year=ano,
        data__month=mes
    ).count()

    if total_ocorrencias > config.limite_mensal:
        alerta, created = AlertaLimiteOcorrenciaRapida.objects.update_or_create(
            estudante=estudante,
            tipo_ocorrencia=config.tipo_ocorrencia,
            mes_referencia=mes_referencia,
            defaults={
                'configuracao': config,
                'quantidade_ocorrencias': total_ocorrencias,
            }
        )
        if created:
            logger.info(f"Novo alerta limite gerado: {estudante} - {config.tipo_ocorrencia}")
    else:
        # Remove alerta se o estudante não excede mais o limite (ex: limite aumentou)
        AlertaLimiteOcorrenciaRapida.objects.filter(
            estudante=estudante,
            tipo_ocorrencia=config.tipo_ocorrencia,
            mes_referencia=mes_referencia
        ).delete()


def recalcular_alertas_periodo(mes_referencia=None):
    """
    Força a verificação de TODOS os estudantes e TODAS as configurações ativas.
    """
    if not mes_referencia:
        mes_referencia = timezone.now().strftime('%Y-%m')

    ano, mes = map(int, mes_referencia.split('-'))
    configs_ativas = ConfiguracaoLimiteOcorrenciaRapida.objects.filter(ativo=True)

    contagem_alertas_gerados = 0

    for config in configs_ativas:
        # CORREÇÃO AQUI: Uso de 'ocorrencias_rapidas' nos filtros e no Count
        estudantes_com_ocorrencias = Estudante.objects.filter(
            ocorrencias_rapidas__tipos_rapidos=config.tipo_ocorrencia,
            ocorrencias_rapidas__data__year=ano,
            ocorrencias_rapidas__data__month=mes
        ).annotate(
            qtd=Count('ocorrencias_rapidas')
        ).filter(
            qtd__gt=config.limite_mensal
        )

        for dados_estudante in estudantes_com_ocorrencias:
            alerta, created = AlertaLimiteOcorrenciaRapida.objects.update_or_create(
                estudante=dados_estudante,
                tipo_ocorrencia=config.tipo_ocorrencia,
                mes_referencia=mes_referencia,
                defaults={
                    'configuracao': config,
                    'quantidade_ocorrencias': dados_estudante.qtd
                }
            )
            contagem_alertas_gerados += 1

    return contagem_alertas_gerados