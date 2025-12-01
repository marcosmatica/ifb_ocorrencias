# Criar novo arquivo: comissao_disciplinar/core/utils_alertas.py

from django.utils import timezone
from django.db.models import Count
from datetime import datetime
from .models import (
    OcorrenciaRapida,
    ConfiguracaoLimiteOcorrenciaRapida,
    AlertaLimiteOcorrenciaRapida,
    Notificacao,
    Servidor
)
from .services import ServicoNotificacao


class VerificadorLimitesOcorrenciaRapida:
    """
    Classe responsável por verificar se estudantes atingiram limites
    de ocorrências rápidas e gerar alertas apropriados
    """

    @staticmethod
    def verificar_e_alertar(ocorrencia_rapida):
        """
        Verifica se algum estudante da ocorrência atingiu limite
        e gera alertas necessários

        Args:
            ocorrencia_rapida: Instância de OcorrenciaRapida recém-criada
        """
        print(f"\n{'=' * 60}")
        print(f"🔍 Verificando limites para Ocorrência Rápida #{ocorrencia_rapida.id}")
        print(f"{'=' * 60}\n")

        # Obter primeiro e último dia do mês atual
        data_ocorrencia = ocorrencia_rapida.data
        primeiro_dia_mes = data_ocorrencia.replace(day=1)

        # Próximo mês
        if data_ocorrencia.month == 12:
            proximo_mes = data_ocorrencia.replace(year=data_ocorrencia.year + 1, month=1, day=1)
        else:
            proximo_mes = data_ocorrencia.replace(month=data_ocorrencia.month + 1, day=1)

        # Para cada tipo de ocorrência selecionado
        for tipo in ocorrencia_rapida.tipos_rapidos.all():
            print(f"📋 Verificando tipo: {tipo.codigo}")

            # Buscar configuração de limite para este tipo
            try:
                config = ConfiguracaoLimiteOcorrenciaRapida.objects.get(
                    tipo_ocorrencia=tipo,
                    ativo=True
                )
                print(f"✅ Configuração encontrada: Limite = {config.limite_mensal}")
            except ConfiguracaoLimiteOcorrenciaRapida.DoesNotExist:
                print(f"⚠️  Nenhuma configuração ativa para {tipo.codigo}")
                continue

            # Para cada estudante envolvido
            for estudante in ocorrencia_rapida.estudantes.all():
                VerificadorLimitesOcorrenciaRapida._verificar_estudante(
                    estudante=estudante,
                    tipo=tipo,
                    config=config,
                    primeiro_dia_mes=primeiro_dia_mes,
                    proximo_mes=proximo_mes
                )

    @staticmethod
    def _verificar_estudante(estudante, tipo, config, primeiro_dia_mes, proximo_mes):
        """
        Verifica um estudante específico para um tipo de ocorrência
        """
        print(f"\n  👤 Estudante: {estudante.nome} ({estudante.matricula_sga})")

        # Contar ocorrências do mesmo tipo no mês
        count = OcorrenciaRapida.objects.filter(
            estudantes=estudante,
            tipos_rapidos=tipo,
            data__gte=primeiro_dia_mes,
            data__lt=proximo_mes
        ).count()

        print(f"  📊 Total de ocorrências do tipo {tipo.codigo} no mês: {count}")
        print(f"  ⚖️  Limite configurado: {config.limite_mensal}")

        # Verificar se atingiu ou ultrapassou o limite
        if count >= config.limite_mensal:
            print(f"  🚨 LIMITE ATINGIDO! ({count} >= {config.limite_mensal})")

            # Verificar se já foi gerado alerta para este estudante/tipo/mês
            alerta_existente = AlertaLimiteOcorrenciaRapida.objects.filter(
                estudante=estudante,
                tipo_ocorrencia=tipo,
                mes_referencia=primeiro_dia_mes
            ).first()

            if alerta_existente:
                print(f"  ℹ️  Alerta já existe. Atualizando contagem...")
                alerta_existente.quantidade_ocorrencias = count
                alerta_existente.save()
            else:
                print(f"  ✨ Criando novo alerta...")
                # Criar novo alerta
                alerta = AlertaLimiteOcorrenciaRapida.objects.create(
                    estudante=estudante,
                    tipo_ocorrencia=tipo,
                    configuracao=config,
                    mes_referencia=primeiro_dia_mes,
                    quantidade_ocorrencias=count
                )

                # Gerar notificações conforme configuração
                VerificadorLimitesOcorrenciaRapida._gerar_notificacoes(
                    alerta=alerta,
                    config=config,
                    estudante=estudante,
                    tipo=tipo,
                    count=count
                )
        else:
            print(f"  ✅ Dentro do limite ({count} < {config.limite_mensal})")

    @staticmethod
    def _gerar_notificacoes(alerta, config, estudante, tipo, count):
        """
        Gera as notificações necessárias conforme configuração
        """
        print(f"\n  {'=' * 50}")
        print(f"  📬 Gerando notificações...")
        print(f"  {'=' * 50}")

        # 1. Notificação no sistema
        if config.gerar_notificacao_sistema:
            VerificadorLimitesOcorrenciaRapida._criar_notificacao_sistema(
                alerta, config, estudante, tipo, count
            )

        # 2. E-mail para coordenação
        if config.gerar_email_coordenacao:
            VerificadorLimitesOcorrenciaRapida._enviar_email_coordenacao(
                alerta, config, estudante, tipo, count
            )

        # 3. E-mail para responsáveis
        if config.gerar_email_responsaveis:
            VerificadorLimitesOcorrenciaRapida._enviar_email_responsaveis(
                alerta, config, estudante, tipo, count
            )

    @staticmethod
    def _criar_notificacao_sistema(alerta, config, estudante, tipo, count):
        """
        Cria notificações no sistema para servidores da coordenação
        """
        try:
            print(f"  🔔 Criando notificação no sistema...")

            # Buscar servidores da coordenação configurada
            servidores = Servidor.objects.filter(
                coordenacao=config.coordenacoes_notificar
            )

            if not servidores.exists():
                print(f"  ⚠️  Nenhum servidor encontrado na coordenação {config.coordenacoes_notificar}")
                return

            titulo = f"⚠️ Alerta: Limite de Ocorrências Atingido"
            mensagem = (
                f"O estudante {estudante.nome} ({estudante.matricula_sga}) "
                f"atingiu {count} ocorrências do tipo '{tipo.codigo}' no mês atual. "
                f"Limite configurado: {config.limite_mensal}. "
                f"Turma: {estudante.turma.nome}."
            )

            # Criar notificação para cada servidor
            for servidor in servidores:
                Notificacao.objects.create(
                    usuario=servidor.user,
                    tipo='ALERTA',
                    titulo=titulo,
                    mensagem=mensagem,
                    prioridade='ALTA',
                    ocorrencia=None  # Não vincula a uma ocorrência específica
                )
                print(f"  ✅ Notificação criada para {servidor.nome}")

            alerta.notificacao_sistema_criada = True
            alerta.save()

        except Exception as e:
            print(f"  ❌ Erro ao criar notificação no sistema: {str(e)}")

    @staticmethod
    def _enviar_email_coordenacao(alerta, config, estudante, tipo, count):
        """
        Envia e-mail para servidores da coordenação
        """
        try:
            print(f"  📧 Enviando e-mail para coordenação...")

            # Buscar servidores da coordenação
            servidores = Servidor.objects.filter(
                coordenacao=config.coordenacoes_notificar
            )

            if not servidores.exists():
                print(f"  ⚠️  Nenhum servidor encontrado")
                return

            emails_destino = [s.email for s in servidores if s.email]

            if not emails_destino:
                print(f"  ⚠️  Nenhum e-mail válido encontrado")
                return

            assunto = f"⚠️ Alerta: Estudante Atingiu Limite de Ocorrências"

            corpo = f"""
Prezado(a) Servidor(a),

Este é um alerta automático do Sistema de Ocorrências.

ESTUDANTE: {estudante.nome}
MATRÍCULA: {estudante.matricula_sga}
TURMA: {estudante.turma.nome}
CURSO: {estudante.curso.nome}

TIPO DE OCORRÊNCIA: {tipo.codigo} - {tipo.descricao}
QUANTIDADE NO MÊS: {count}
LIMITE CONFIGURADO: {config.limite_mensal}

⚠️ O estudante atingiu ou ultrapassou o limite mensal de ocorrências rápidas 
do tipo "{tipo.codigo}".

Recomenda-se:
- Análise do histórico completo do estudante
- Contato com responsáveis
- Avaliação de medidas pedagógicas preventivas
- Possível encaminhamento para atendimento especializado

Para mais detalhes, acesse o sistema:
{ServicoNotificacao._get_base_url()}/estudantes/{estudante.matricula_sga}/

Atenciosamente,
Sistema de Ocorrências - IFB
"""

            ServicoNotificacao._enviar_email_generico(
                assunto=assunto,
                corpo=corpo,
                destinatarios=emails_destino
            )

            alerta.email_coordenacao_enviado = True
            alerta.save()

            print(f"  ✅ E-mail enviado para {len(emails_destino)} servidor(es)")

        except Exception as e:
            print(f"  ❌ Erro ao enviar e-mail para coordenação: {str(e)}")

    @staticmethod
    def _enviar_email_responsaveis(alerta, config, estudante, tipo, count):
        """
        Envia e-mail para responsáveis do estudante
        """
        try:
            print(f"  📧 Enviando e-mail para responsáveis...")

            responsaveis = estudante.responsaveis.all()

            if not responsaveis.exists():
                print(f"  ⚠️  Nenhum responsável cadastrado")
                return

            emails_destino = [r.email for r in responsaveis if r.email]

            if not emails_destino:
                print(f"  ⚠️  Nenhum e-mail de responsável válido")
                return

            assunto = f"Comunicado: Ocorrências Frequentes - {estudante.nome}"

            corpo = f"""
Prezado(a) Responsável,

Informamos que o(a) estudante {estudante.nome}, matrícula {estudante.matricula_sga},
da turma {estudante.turma.nome}, apresentou {count} ocorrências do tipo 
"{tipo.codigo}" no mês atual.

DESCRIÇÃO DO TIPO: {tipo.descricao}

Este é um comunicado automático gerado pelo nosso sistema de acompanhamento 
pedagógico, visando manter os responsáveis informados sobre o comportamento 
acadêmico do(a) estudante.

Solicitamos atenção especial a este aspecto e, se necessário, comparecer à 
escola para uma conversa com a equipe pedagógica.

Para mais informações, entre em contato:
- Coordenação Pedagógica: comissao.disciplinar@ifb.edu.br
- Telefone: (61) 2103-2100

Atenciosamente,
Instituto Federal de Brasília - Campus Recanto das Emas
"""

            ServicoNotificacao._enviar_email_generico(
                assunto=assunto,
                corpo=corpo,
                destinatarios=emails_destino
            )

            alerta.email_responsaveis_enviado = True
            alerta.save()

            print(f"  ✅ E-mail enviado para {len(emails_destino)} responsável(is)")

        except Exception as e:
            print(f"  ❌ Erro ao enviar e-mail para responsáveis: {str(e)}")