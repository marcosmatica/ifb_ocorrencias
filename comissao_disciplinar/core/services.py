# core/services.py - VERSÃO COMPLETA
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notificacao, PreferenciaNotificacao
import requests
from typing import List, Optional


class ServicoNotificacao:
    @staticmethod
    def criar_notificacao(usuario, tipo, titulo, mensagem, ocorrencia=None, prioridade='MEDIA'):
        """Cria uma notificação in-app para o usuário"""
        notificacao = Notificacao.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            ocorrencia=ocorrencia,
            prioridade=prioridade
        )

        # Se for notificação urgente, enviar e-mail também
        if prioridade in ['ALTA', 'URGENTE']:
            ServicoNotificacao.enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia)

        return notificacao

    @staticmethod
    def enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia=None):
        """Envia notificação por e-mail"""
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
            send_mail(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                [usuario.email],
                html_message=mensagem_html,
                fail_silently=False
            )
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")

    @staticmethod
    def notificar_responsaveis_ocorrencia(ocorrencia, tipo_ocorrencia='ocorrencia'):
        """
        Notifica os responsáveis via e-mail e SMS sobre uma ocorrência

        Args:
            ocorrencia: Instância de Ocorrencia ou OcorrenciaRapida
            tipo_ocorrencia: 'ocorrencia' ou 'ocorrencia_rapida'
        """
        from .models import Estudante

        # Coletar todos os responsáveis únicos
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

        # Enviar notificações para cada responsável
        for resp_data in responsaveis_unicos.values():
            responsavel = resp_data['responsavel']
            estudantes_lista = resp_data['estudantes']

            # Enviar E-MAIL
            ServicoNotificacao._enviar_email_responsavel(
                responsavel,
                estudantes_lista,
                ocorrencia,
                tipo_ocorrencia
            )

            # Enviar SMS
            ServicoNotificacao._enviar_sms_responsavel(
                responsavel,
                estudantes_lista,
                ocorrencia,
                tipo_ocorrencia
            )

    @staticmethod
    def _enviar_email_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia e-mail para o responsável"""
        try:
            # Verificar preferência de contato
            if responsavel.preferencia_contato not in ['EMAIL', 'WHATSAPP']:
                return

            estudantes_nomes = ", ".join([e.nome for e in estudantes])

            # Template diferente para cada tipo
            if tipo_ocorrencia == 'ocorrencia_rapida':
                template_html = 'email/notificacao_responsavel_rapida.html'
                template_text = 'email/notificacao_responsavel_rapida.txt'
                assunto = f"[IFB] Registro de Ocorrência - {estudantes_nomes}"
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
                'marcos.rodrigues@ifb.edu.br'#[responsavel.email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            email.send()

            print(f"✅ E-mail enviado para {responsavel.nome} ({responsavel.email})")

        except Exception as e:
            print(f"❌ Erro ao enviar e-mail para {responsavel.nome}: {str(e)}")

    @staticmethod
    def _enviar_sms_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia SMS para o responsável"""
        try:
            # Verificar preferência de contato
            if responsavel.preferencia_contato not in ['CELULAR', 'WHATSAPP']:
                return

            estudantes_nomes = estudantes[0].nome if len(estudantes) == 1 else f"{len(estudantes)} estudantes"

            # Mensagem curta para SMS
            if tipo_ocorrencia == 'ocorrencia_rapida':
                tipo_display = dict(ocorrencia.TIPOS_RAPIDOS).get(ocorrencia.tipo_rapido, 'Ocorrência')
                mensagem = (
                    f"IFB - Registro: {tipo_display} envolvendo {estudantes_nomes} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Mais informações serão enviadas por e-mail."
                )
            else:
                mensagem = (
                    f"IFB - Ocorrência disciplinar envolvendo {estudantes_nomes} "
                    f"registrada em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Detalhes no e-mail enviado."
                )

            # Enviar via serviço de SMS (escolha um dos métodos abaixo)
            ServicoNotificacao._enviar_sms_via_twilio(responsavel.celular, mensagem)
            # OU
            # ServicoNotificacao._enviar_sms_via_zenvia(responsavel.celular, mensagem)

        except Exception as e:
            print(f"❌ Erro ao enviar SMS para {responsavel.nome}: {str(e)}")

    @staticmethod
    def _enviar_sms_via_twilio(numero, mensagem):
        """Envia SMS usando Twilio"""
        try:
            # Importar apenas se configurado
            if not hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                print("⚠️ Twilio não configurado")
                return

            from twilio.rest import Client

            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )

            message = client.messages.create(
                body=mensagem,
                from_=settings.TWILIO_PHONE_NUMBER,
                to='+5561983512360'#numero
            )

            print(f"✅ SMS enviado via Twilio para {numero}: {message.sid}")

        except Exception as e:
            print(f"❌ Erro ao enviar SMS via Twilio: {str(e)}")

    @staticmethod
    def _enviar_sms_via_zenvia(numero, mensagem):
        """Envia SMS usando Zenvia (alternativa brasileira)"""
        try:
            if not hasattr(settings, 'ZENVIA_API_TOKEN'):
                print("⚠️ Zenvia não configurado")
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
                print(f"✅ SMS enviado via Zenvia para {numero}")
            else:
                print(f"❌ Erro Zenvia: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Erro ao enviar SMS via Zenvia: {str(e)}")

    @staticmethod
    def notificar_nova_ocorrencia(ocorrencia):
        """Notifica sobre nova ocorrência para a comissão disciplinar"""
        from django.contrib.auth.models import User
        from .models import Servidor

        # Notificar membros da comissão disciplinar
        membros_comissao = Servidor.objects.filter(membro_comissao_disciplinar=True)

        for servidor in membros_comissao:
            ServicoNotificacao.criar_notificacao(
                usuario=servidor.user,
                tipo='NOVA_OCORRENCIA',
                titulo=f'Nova Ocorrência #{ocorrencia.id}',
                mensagem=f'Foi registrada uma nova ocorrência por {ocorrencia.responsavel_registro.nome}',
                ocorrencia=ocorrencia,
                prioridade='ALTA' if ocorrencia.infracao and ocorrencia.infracao.gravidade in ['GRAVE',
                                                                                               'GRAVISSIMA'] else 'MEDIA'
            )

    @staticmethod
    def notificar_mudanca_status(ocorrencia, status_anterior):
        """Notifica sobre mudança de status da ocorrência"""
        # Notificar responsável pelo registro
        ServicoNotificacao.criar_notificacao(
            usuario=ocorrencia.responsavel_registro.user,
            tipo='ATUALIZACAO_STATUS',
            titulo=f'Ocorrência #{ocorrencia.id} - Status Alterado',
            mensagem=f'O status da ocorrência mudou de {status_anterior} para {ocorrencia.status}',
            ocorrencia=ocorrencia,
            prioridade='MEDIA'
        )

        # Notificar comissão se for mudança importante
        if ocorrencia.status in ['EM_ANALISE', 'EM_JULGAMENTO']:
            from .models import Servidor
            membros_comissao = Servidor.objects.filter(membro_comissao_disciplinar=True)

            for servidor in membros_comissao:
                if servidor.user != ocorrencia.responsavel_registro.user:
                    ServicoNotificacao.criar_notificacao(
                        usuario=servidor.user,
                        tipo='ATUALIZACAO_STATUS',
                        titulo=f'Ocorrência #{ocorrencia.id} - Status Alterado',
                        mensagem=f'O status da ocorrência mudou para {ocorrencia.status}',
                        ocorrencia=ocorrencia,
                        prioridade='MEDIA'
                    )