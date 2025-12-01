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
    # Conta ocorrências desse tipo para esse estudante no mês
    # Ajuste: Filtramos pela data da ocorrência (ano e mês)
    ano, mes = map(int, mes_referencia.split('-'))

    total_ocorrencias = OcorrenciaRapida.objects.filter(
        estudantes=estudante,
        tipos_rapidos=config.tipo_ocorrencia,
        data__year=ano,
        data__month=mes
    ).count()

    # Se ultrapassou o limite
    if total_ocorrencias > config.limite_mensal:
        alerta, created = AlertaLimiteOcorrenciaRapida.objects.update_or_create(
            estudante=estudante,
            tipo_ocorrencia=config.tipo_ocorrencia,
            mes_referencia=mes_referencia,
            defaults={
                'configuracao': config,
                'quantidade_ocorrencias': total_ocorrencias,
                # Mantemos os status de envio se já existiam, senão False
                # Não resetamos notificacao_sistema_criada para não spamar se já foi criado
            }
        )
        if created:
            logger.info(f"Novo alerta limite gerado: {estudante} - {config.tipo_ocorrencia}")
    else:
        # Opcional: Se o limite foi aumentado e o estudante não excede mais,
        # podemos remover o alerta ou deixá-lo como histórico.
        # Aqui optamos por deletar alertas que não são mais válidos (ex: limite subiu)
        AlertaLimiteOcorrenciaRapida.objects.filter(
            estudante=estudante,
            tipo_ocorrencia=config.tipo_ocorrencia,
            mes_referencia=mes_referencia
        ).delete()


def recalcular_alertas_periodo(mes_referencia=None):
    """
    Força a verificação de TODOS os estudantes e TODAS as configurações ativas.
    Essencial para quando o admin altera os limites.

    Args:
        mes_referencia (str): Formato 'YYYY-MM'. Se None, usa o mês atual.
    """
    if not mes_referencia:
        mes_referencia = timezone.now().strftime('%Y-%m')

    ano, mes = map(int, mes_referencia.split('-'))
    configs_ativas = ConfiguracaoLimiteOcorrenciaRapida.objects.filter(ativo=True)

    contagem_alertas_gerados = 0

    for config in configs_ativas:
        # Otimização: Agrega contagem diretamente no banco
        # Pega estudantes que têm ocorrências desse tipo no mês
        estudantes_com_ocorrencias = Estudante.objects.filter(
            ocorrenciarapida__tipos_rapidos=config.tipo_ocorrencia,
            ocorrenciarapida__data__year=ano,
            ocorrenciarapida__data__month=mes
        ).annotate(
            qtd=Count('ocorrenciarapida')
        ).filter(
            qtd__gt=config.limite_mensal  # Filtra apenas quem ESTOUROU o limite
        )

        for dados_estudante in estudantes_com_ocorrencias:
            # Update_or_create garante que atualizamos o contador se o alerta já existir
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