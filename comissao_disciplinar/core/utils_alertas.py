# core/utils_alertas.py - ATUALIZE ESTA FUNÇÃO COMPLETAMENTE
from django.utils import timezone
from django.db.models import Count, Q
from datetime import date, timedelta
from .models import (
    OcorrenciaRapida,
    ConfiguracaoLimiteOcorrenciaRapida,
    AlertaLimiteOcorrenciaRapida,
    Estudante,
    TipoOcorrenciaRapida
)
import logging

logger = logging.getLogger(__name__)


def verificar_limites_ocorrencia(ocorrencia):
    """
    Verifica se uma ocorrência específica dispara algum alerta.
    Usado em signals ou no save_model.
    """
    try:
        estudantes = ocorrencia.estudantes.all()
        tipos = ocorrencia.tipos_rapidos.all()

        if not estudantes or not tipos:
            return

        # Data da ocorrência define o mês de referência
        mes_referencia = ocorrencia.data.replace(day=1)

        logger.info(f"Verificando limites para {estudantes.count()} estudantes e {tipos.count()} tipos")

        # Filtra configurações ativas para os tipos desta ocorrência
        configs = ConfiguracaoLimiteOcorrenciaRapida.objects.filter(
            tipo_ocorrencia__in=tipos,
            ativo=True
        ).select_related('tipo_ocorrencia')

        logger.info(f"Encontradas {configs.count()} configurações ativas")

        for config in configs:
            for estudante in estudantes:
                processar_alerta_individual(estudante, config, mes_referencia)

    except Exception as e:
        logger.error(f"Erro ao verificar limites: {str(e)}")


def processar_alerta_individual(estudante, config, mes_referencia):
    """
    Lógica isolada para verificar e criar/atualizar alerta para um estudante/config específico.
    """
    try:
        ano = mes_referencia.year
        mes = mes_referencia.month

        # Contar ocorrências do tipo específico para este estudante no mês
        total_ocorrencias = OcorrenciaRapida.objects.filter(
            estudantes=estudante,
            tipos_rapidos=config.tipo_ocorrencia,
            data__year=ano,
            data__month=mes
        ).count()

        logger.info(
            f"Estudante {estudante.nome} - Tipo {config.tipo_ocorrencia.codigo}: {total_ocorrencias}/{config.limite_mensal}")

        if total_ocorrencias >= config.limite_mensal:  # Alterado para >= para incluir quando igual ao limite
            alerta, created = AlertaLimiteOcorrenciaRapida.objects.update_or_create(
                estudante=estudante,
                tipo_ocorrencia=config.tipo_ocorrencia,
                mes_referencia=mes_referencia,
                defaults={
                    'configuracao': config,
                    'quantidade_ocorrencias': total_ocorrencias,
                }
            )

            # Enviar notificações se configurado
            if created and config.gerar_notificacao_sistema:
                from .services import ServicoNotificacao
                try:
                    ServicoNotificacao.notificar_alerta_limite_atingido(alerta)
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação: {str(e)}")

            if created:
                logger.info(
                    f"✅ Alerta criado: {estudante.nome} - {config.tipo_ocorrencia.codigo} ({total_ocorrencias}x)")

        else:
            # Remover alerta se o estudante não excede mais o limite
            deleted, _ = AlertaLimiteOcorrenciaRapida.objects.filter(
                estudante=estudante,
                tipo_ocorrencia=config.tipo_ocorrencia,
                mes_referencia=mes_referencia
            ).delete()

            if deleted:
                logger.info(f"❌ Alerta removido: {estudante.nome} - {config.tipo_ocorrencia.codigo}")

    except Exception as e:
        logger.error(f"Erro ao processar alerta para {estudante.nome}: {str(e)}")


def recalcular_alertas_periodo(mes_referencia=None):
    """
    Força a verificação de TODOS os estudantes e TODAS as configurações ativas.
    Retorna estatísticas detalhadas.

    Args:
        mes_referencia: Data do primeiro dia do mês (datetime.date)

    Returns:
        dict com estatísticas do recálculo
    """
    if not mes_referencia:
        mes_referencia = timezone.now().date().replace(day=1)

    logger.info(f"🔍 RECALCULANDO ALERTAS para {mes_referencia.strftime('%m/%Y')}")
    print(f"\n{'=' * 60}")
    print(f"🔍 RECALCULANDO ALERTAS para {mes_referencia.strftime('%m/%Y')}")
    print(f"{'=' * 60}\n")

    ano = mes_referencia.year
    mes = mes_referencia.month

    # Limpar alertas existentes para este mês
    deleted_count = AlertaLimiteOcorrenciaRapida.objects.filter(
        mes_referencia=mes_referencia
    ).delete()[0]

    logger.info(f"Limpos {deleted_count} alertas antigos")
    print(f"🗑️  Limpos {deleted_count} alertas antigos")

    # Obter TODAS as configurações ativas
    configs_ativas = ConfiguracaoLimiteOcorrenciaRapida.objects.filter(
        ativo=True
    ).select_related('tipo_ocorrencia')

    if not configs_ativas.exists():
        logger.warning("⚠️ Nenhuma configuração ativa encontrada!")
        print("⚠️ Nenhuma configuração ativa encontrada!")
        return {
            'configuracoes_processadas': 0,
            'alertas_gerados': 0,
            'estudantes_afetados': 0,
            'mes_referencia': mes_referencia.strftime('%m/%Y')
        }

    logger.info(f"📊 Configurações ativas: {configs_ativas.count()}")
    print(f"📊 Configurações ativas: {configs_ativas.count()}")

    alertas_gerados = 0
    estudantes_afetados = set()

    for config in configs_ativas:
        logger.info(f"\nProcessando {config.tipo_ocorrencia.codigo} (limite: {config.limite_mensal})")
        print(f"\n📋 Processando {config.tipo_ocorrencia.codigo} (limite: {config.limite_mensal})")

        # Buscar estudantes com ocorrências deste tipo no mês
        estudantes_com_ocorrencias = Estudante.objects.filter(
            ocorrencias_rapidas__tipos_rapidos=config.tipo_ocorrencia,
            ocorrencias_rapidas__data__year=ano,
            ocorrencias_rapidas__data__month=mes
        ).annotate(
            qtd=Count('ocorrencias_rapidas', distinct=True)
        ).filter(
            qtd__gte=config.limite_mensal
        ).distinct()

        logger.info(f"  → {estudantes_com_ocorrencias.count()} estudantes excedem o limite")
        print(f"  → {estudantes_com_ocorrencias.count()} estudantes excedem o limite")

        for estudante in estudantes_com_ocorrencias:
            try:
                # Contar novamente para garantir precisão
                total_ocorrencias = OcorrenciaRapida.objects.filter(
                    estudantes=estudante,
                    tipos_rapidos=config.tipo_ocorrencia,
                    data__year=ano,
                    data__month=mes
                ).count()

                print(f"    📌 {estudante.nome}: {total_ocorrencias} ocorrências")

                if total_ocorrencias >= config.limite_mensal:
                    alerta, created = AlertaLimiteOcorrenciaRapida.objects.get_or_create(
                        estudante=estudante,
                        tipo_ocorrencia=config.tipo_ocorrencia,
                        mes_referencia=mes_referencia,
                        defaults={
                            'configuracao': config,
                            'quantidade_ocorrencias': total_ocorrencias
                        }
                    )

                    if not created:
                        # Atualizar quantidade se já existir
                        alerta.quantidade_ocorrencias = total_ocorrencias
                        alerta.save(update_fields=['quantidade_ocorrencias'])

                    alertas_gerados += 1
                    estudantes_afetados.add(estudante.id)

                    logger.info(f"    ✅ {estudante.nome}: {total_ocorrencias} ocorrências")

            except Exception as e:
                logger.error(f"Erro ao criar alerta para {estudante.nome}: {str(e)}")
                print(f"    ❌ Erro: {str(e)}")

    logger.info(f"\n🎯 CONCLUSÃO: {alertas_gerados} alertas gerados para {len(estudantes_afetados)} estudantes")
    print(f"\n{'=' * 60}")
    print(f"🎯 CONCLUSÃO: {alertas_gerados} alertas gerados")
    print(f"👥 Estudantes afetados: {len(estudantes_afetados)}")
    print(f"{'=' * 60}\n")

    return {
        'configuracoes_processadas': configs_ativas.count(),
        'alertas_gerados': alertas_gerados,
        'estudantes_afetados': len(estudantes_afetados),
        'mes_referencia': mes_referencia.strftime('%m/%Y')
    }