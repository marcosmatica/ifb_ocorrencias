# core/services.py - Sistema Completo de Notificações
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notificacao, PreferenciaNotificacao
import requests
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ServicoNotificacao:
    """Serviço centralizado para envio de notificações"""

    @staticmethod
    def criar_notificacao(usuario, tipo, titulo, mensagem, ocorrencia=None, prioridade='MEDIA'):
        """Cria notificação in-app"""
        notificacao = Notificacao.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            ocorrencia=ocorrencia,
            prioridade=prioridade
        )

        if prioridade in ['ALTA', 'URGENTE']:
            ServicoNotificacao.enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia)

        return notificacao

    @staticmethod
    def enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia=None):
        """Envia notificação por email"""
        try:
            preferencias = PreferenciaNotificacao.objects.get(usuario=usuario)
            if not preferencias.receber_notificacoes_urgentes:
                return
        except PreferenciaNotificacao.DoesNotExist:
            PreferenciaNotificacao.objects.create(usuario=usuario)

        assunto = f"[Sistema Ocorrências IFB] {titulo}"
        contexto = {
            'titulo': titulo,
            'mensagem': mensagem,
            'ocorrencia': ocorrencia,
            'usuario': usuario
        }

        mensagem_html = render_to_string('email/notificacao_urgente.html', contexto)
        mensagem_texto = render_to_string('email/notificacao_urgente.txt', contexto)

        try:
            email = EmailMultiAlternatives(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                [usuario.email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            email.send()
            logger.info(f"✅ Email enviado para {usuario.email}")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")

    @staticmethod
    def notificar_responsaveis_ocorrencia(ocorrencia, tipo_ocorrencia='ocorrencia'):
        """
        Notifica responsáveis via email e SMS sobre ocorrências

        Args:
            ocorrencia: Instância de Ocorrencia ou OcorrenciaRapida
            tipo_ocorrencia: 'ocorrencia' ou 'ocorrencia_rapida'
        """
        # Coletar responsáveis únicos
        responsaveis_unicos = {}
        estudantes = ocorrencia.estudantes.all()

        for estudante in estudantes:
            for responsavel in estudante.responsaveis.all():
                if responsavel.id not in responsaveis_unicos:
                    responsaveis_unicos[responsavel.id] = {
                        'responsavel': responsavel,
                        'estudantes': []
                    }
                responsaveis_unicos[responsavel.id]['estudantes'].append(estudante)

        # Enviar notificações
        for resp_data in responsaveis_unicos.values():
            responsavel = resp_data['responsavel']
            estudantes_lista = resp_data['estudantes']

            # Email
            ServicoNotificacao._enviar_email_responsavel(
                responsavel, estudantes_lista, ocorrencia, tipo_ocorrencia
            )

            # SMS
            ServicoNotificacao._enviar_sms_responsavel(
                responsavel, estudantes_lista, ocorrencia, tipo_ocorrencia
            )

    @staticmethod
    def _enviar_email_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia email para responsável"""
        try:
            if responsavel.preferencia_contato not in ['EMAIL', 'WHATSAPP']:
                return

            estudantes_nomes = ", ".join([e.nome for e in estudantes])

            if tipo_ocorrencia == 'ocorrencia_rapida':
                template_html = 'email/notificacao_responsavel_rapida.html'
                template_text = 'email/notificacao_responsavel_rapida.txt'
                assunto = f"[IFB] Registro - {estudantes_nomes}"
            else:
                template_html = 'email/notificacao_responsavel_ocorrencia.html'
                template_text = 'email/notificacao_responsavel_ocorrencia.txt'
                assunto = f"[IFB] Ocorrência Disciplinar - {estudantes_nomes}"

            contexto = {
                'responsavel': responsavel,
                'estudantes': estudantes,
                'ocorrencia': ocorrencia,
                'tipo_ocorrencia': tipo_ocorrencia,
            }

            mensagem_html = render_to_string(template_html, contexto)
            mensagem_texto = render_to_string(template_text, contexto)

            email = EmailMultiAlternatives(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                [responsavel.email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            email.send()

            logger.info(f"✅ Email enviado para {responsavel.nome} ({responsavel.email})")

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email para {responsavel.nome}: {str(e)}")

    @staticmethod
    def _enviar_sms_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia SMS para responsável"""
        try:
            if responsavel.preferencia_contato not in ['CELULAR', 'WHATSAPP']:
                return

            estudantes_nomes = estudantes[0].nome if len(estudantes) == 1 else f"{len(estudantes)} estudantes"

            if tipo_ocorrencia == 'ocorrencia_rapida':
                tipo_display = dict(ocorrencia.TIPOS_RAPIDOS).get(ocorrencia.tipo_rapido, 'Ocorrência')
                mensagem = (
                    f"IFB - Registro: {tipo_display} envolvendo {estudantes_nomes} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Mais informações no email."
                )
            else:
                mensagem = (
                    f"IFB - Ocorrência disciplinar envolvendo {estudantes_nomes} "
                    f"registrada em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Detalhes no email enviado."
                )

            # Tentar Twilio primeiro, depois Zenvia
            if hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                ServicoNotificacao._enviar_sms_via_twilio(responsavel.celular, mensagem)
            elif hasattr(settings, 'ZENVIA_API_TOKEN'):
                ServicoNotificacao._enviar_sms_via_zenvia(responsavel.celular, mensagem)
            else:
                logger.warning("⚠️ Nenhum provedor SMS configurado")

        except Exception as e:
            logger.error(f"❌ Erro ao enviar SMS para {responsavel.nome}: {str(e)}")

    @staticmethod
    def _enviar_sms_via_twilio(numero, mensagem):
        """Envia SMS via Twilio"""
        try:
            if not hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                logger.warning("⚠️ Twilio não configurado")
                return

            from twilio.rest import Client

            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )

            message = client.messages.create(
                body=mensagem,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=numero
            )

            logger.info(f"✅ SMS Twilio enviado para {numero}: {message.sid}")

        except Exception as e:
            logger.error(f"❌ Erro Twilio: {str(e)}")

    @staticmethod
    def _enviar_sms_via_zenvia(numero, mensagem):
        """Envia SMS via Zenvia (alternativa brasileira)"""
        try:
            if not hasattr(settings, 'ZENVIA_API_TOKEN'):
                logger.warning("⚠️ Zenvia não configurado")
                return

            url = "https://api.zenvia.com/v2/channels/sms/messages"

            headers = {
                "X-API-TOKEN": settings.ZENVIA_API_TOKEN,
                "Content-Type": "application/json"
            }

            payload = {
                "from": settings.ZENVIA_SENDER_ID,
                "to": numero,
                "contents": [{
                    "type": "text",
                    "text": mensagem
                }]
            }

            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info(f"✅ SMS Zenvia enviado para {numero}")
            else:
                logger.error(f"❌ Erro Zenvia: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ Erro Zenvia: {str(e)}")

    @staticmethod
    def notificar_nova_ocorrencia(ocorrencia):
        """Notifica comissão sobre nova ocorrência"""
        from .models import Servidor

        membros_comissao = Servidor.objects.filter(membro_comissao_disciplinar=True)

        for servidor in membros_comissao:
            prioridade = 'ALTA' if (
                    ocorrencia.infracao and
                    ocorrencia.infracao.gravidade in ['GRAVE', 'GRAVISSIMA']
            ) else 'MEDIA'

            ServicoNotificacao.criar_notificacao(
                usuario=servidor.user,
                tipo='NOVA_OCORRENCIA',
                titulo=f'Nova Ocorrência #{ocorrencia.id}',
                mensagem=f'Registrada por {ocorrencia.responsavel_registro.nome}',
                ocorrencia=ocorrencia,
                prioridade=prioridade
            )

    @staticmethod
    def notificar_mudanca_status(ocorrencia, status_anterior):
        """Notifica sobre mudança de status"""
        ServicoNotificacao.criar_notificacao(
            usuario=ocorrencia.responsavel_registro.user,
            tipo='ATUALIZACAO_STATUS',
            titulo=f'Ocorrência #{ocorrencia.id} - Status Alterado',
            mensagem=f'Status mudou de {status_anterior} para {ocorrencia.status}',
            ocorrencia=ocorrencia,
            prioridade='MEDIA'
        )

        if ocorrencia.status in ['EM_ANALISE', 'EM_JULGAMENTO']:
            from .models import Servidor
            membros = Servidor.objects.filter(membro_comissao_disciplinar=True)

            for servidor in membros:
                if servidor.user != ocorrencia.responsavel_registro.user:
                    ServicoNotificacao.criar_notificacao(
                        usuario=servidor.user,
                        tipo='ATUALIZACAO_STATUS',
                        titulo=f'Ocorrência #{ocorrencia.id} - Status Alterado',
                        mensagem=f'Status mudou para {ocorrencia.status}',
                        ocorrencia=ocorrencia,
                        prioridade='MEDIA'
                    )