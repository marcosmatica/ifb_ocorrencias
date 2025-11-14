# core/services.py - Versão com DEBUG COMPLETO
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
    def notificar_responsaveis_ocorrencia(ocorrencia, tipo_ocorrencia='ocorrencia'):
        """
        Notifica responsáveis via email e SMS sobre ocorrências
        """
        print(f"\n{'=' * 60}")
        print(f" INICIANDO NOTIFICAÇÃO DOS RESPONSÁVEIS")
        print(f"{'=' * 60}")
        print(f" Ocorrência ID: {ocorrencia.id}")
        print(f" Tipo: {tipo_ocorrencia}")

        # Coletar responsáveis únicos
        responsaveis_unicos = {}
        estudantes = ocorrencia.estudantes.all()
        print(f" Total de estudantes: {estudantes.count()}")

        for estudante in estudantes:
            print(f"\n Estudante: {estudante.nome}")
            print(f"   Matrícula: {estudante.matricula_sga}")

            responsaveis = estudante.responsaveis.all()
            print(f"   Responsáveis cadastrados: {responsaveis.count()}")

            for responsavel in responsaveis:
                print(f"\n   📋 Responsável: {responsavel.nome}")
                print(f"      Email: {responsavel.email}")
                print(f"      Celular: {responsavel.celular}")
                print(f"      Preferência: {responsavel.get_preferencia_contato_display()}")

                if responsavel.id not in responsaveis_unicos:
                    responsaveis_unicos[responsavel.id] = {
                        'responsavel': responsavel,
                        'estudantes': []
                    }
                responsaveis_unicos[responsavel.id]['estudantes'].append(estudante)

        print(f"\n Total de responsáveis únicos: {len(responsaveis_unicos)}")

        # Enviar notificações
        for resp_id, resp_data in responsaveis_unicos.items():
            responsavel = resp_data['responsavel']
            estudantes_lista = resp_data['estudantes']

            print(f"\n{'=' * 60}")
            print(f" Processando responsável: {responsavel.nome}")
            print(f"{'=' * 60}")

            # Email
            try:
                print(f"\n Tentando enviar EMAIL...")
                ServicoNotificacao._enviar_email_responsavel(
                    responsavel, estudantes_lista, ocorrencia, tipo_ocorrencia
                )
            except Exception as e:
                print(f" ERRO ao enviar email: {str(e)}")
                import traceback
                traceback.print_exc()

            # SMS
            try:
                print(f"\n Tentando enviar SMS...")
                ServicoNotificacao._enviar_sms_responsavel(
                    responsavel, estudantes_lista, ocorrencia, tipo_ocorrencia
                )
            except Exception as e:
                print(f" ERRO ao enviar SMS: {str(e)}")
                import traceback
                traceback.print_exc()

        print(f"\n{'=' * 60}")
        print(f" PROCESSO DE NOTIFICAÇÃO CONCLUÍDO")
        print(f"{'=' * 60}\n")

    @staticmethod
    def _enviar_email_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia email para responsável"""
        print(f"\n{'=' * 60}")
        print(f" _enviar_email_responsavel")
        print(f"{'=' * 60}")
        print(f" Responsável: {responsavel.nome}")
        print(f" Email: {responsavel.email}")
        print(f" Preferência: {responsavel.get_preferencia_contato_display()}")

        try:
            if responsavel.preferencia_contato not in ['E-mail', 'CELULAR', 'EMAIL', 'Email']:
                print(f"  Preferência não é EMAIL/WHATSAPP - Pulando")
                return

            # Verificar configurações de email
            print(f"\n Verificando configurações de email...")
            print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
            print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
            print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
            print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

            # Formatar informações dos estudantes
            estudantes_info = []
            for estudante in estudantes:
                primeiro_nome = estudante.nome.split()[0] if estudante.nome else "Estudante"
                nome_abreviado = primeiro_nome + " ..."
                matricula_abreviada = estudante.matricula_sga
                estudantes_info.append(f"{nome_abreviado} ({matricula_abreviada})")

            estudantes_str = ", ".join(estudantes_info)
            print(f"   Estudantes: {estudantes_str}")

            # Definir templates
            if tipo_ocorrencia == 'ocorrencia_rapida':
                template_html = 'email/notificacao_responsavel_rapida.html'
                template_text = 'email/notificacao_responsavel_rapida.txt'
                assunto = f"[IFB] Registro - {estudantes_str}"
            else:
                template_html = 'email/notificacao_responsavel_ocorrencia.html'
                template_text = 'email/notificacao_responsavel_ocorrencia.txt'
                assunto = f"[IFB] Registro Disciplinar - {estudantes_str}"

            print(f"\n Templates:")
            print(f"   HTML: {template_html}")
            print(f"   TEXT: {template_text}")
            print(f"   Assunto: {assunto}")

            contexto = {
                'responsavel': responsavel,
                'estudantes': estudantes,
                'estudantes_str': estudantes_str,
                'ocorrencia': ocorrencia,
                'tipo_ocorrencia': tipo_ocorrencia,
            }

            print(f"\n Renderizando templates...")
            try:
                mensagem_html = render_to_string(template_html, contexto)
                mensagem_texto = render_to_string(template_text, contexto)
                print(f"    Templates renderizados")
                print(f"   HTML length: {len(mensagem_html)} chars")
                print(f"   TEXT length: {len(mensagem_texto)} chars")
            except Exception as e:
                print(f"    ERRO ao renderizar templates: {str(e)}")
                raise

            print(f"\n Criando email...")
            destinatario_email = 'marcos.rodrigues@ifb.edu.br'  # Email de teste
            print(f"   Destinatário: {destinatario_email}")

            email = EmailMultiAlternatives(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                ['marcos.rodrigues@ifb.edu.br']#[destinatario_email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            print(f"    Email criado")

            print(f"\n Enviando email...")
            email.send()
            print(f"    Email enviado com SUCESSO!")

            logger.info(f" Email enviado para {responsavel.nome} ({destinatario_email})")

        except Exception as e:
            print(f"\n ERRO FATAL ao enviar email:")
            print(f"   {str(e)}")
            logger.error(f" Erro ao enviar email para {responsavel.nome}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _enviar_sms_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """Envia SMS para responsável"""
        print(f"\n{'=' * 60}")
        print(f" _enviar_sms_responsavel")
        print(f"{'=' * 60}")
        print(f" Responsável: {responsavel.nome}")
        print(f" Celular: {responsavel.celular}")
        print(f" Preferência: {responsavel.get_preferencia_contato_display()}")

        try:
            if responsavel.preferencia_contato not in ['CELULAR', 'WHATSAPP', 'E-mail', 'EMAIL', 'Email']:
                print(f"  Preferência não é CELULAR/WHATSAPP - Pulando")
                return

            # Verificar configuração Twilio
            print(f"\n Verificando configurações Twilio...")
            has_twilio = hasattr(settings, 'TWILIO_ACCOUNT_SID')
            print(f"   TWILIO_ACCOUNT_SID existe: {has_twilio}")

            if has_twilio:
                print(f"   TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID[:10]}...")
                print(f"   TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
            else:
                print(f"     Twilio não configurado")
                return

            # Formatar mensagem
            if len(estudantes) == 1:
                estudante = estudantes[0]
                primeiro_nome = estudante.nome.split()[0] if estudante.nome else "Estudante"
                #nome_abreviado = primeiro_nome[:3] + "."
                estudantes_info = f"{primeiro_nome} ({estudante.matricula_sga})"
            else:
                estudantes_info = f"{len(estudantes)} estudantes"

            parte_local, dominio = responsavel.email.split('@')
            parte_local_ = parte_local[:5] + '*' * (len(parte_local) - 5)
            texto_email = parte_local_ + '@' + dominio
            if tipo_ocorrencia == 'ocorrencia_rapida':
                tipo_display = dict(ocorrencia.TIPOS_RAPIDOS).get(ocorrencia.tipo_rapido, 'Registro')
                mensagem = (
                    f"IFB - {tipo_display} envolvendo {estudantes_info} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Consulte o email {texto_email} para detalhes."
                )
            else:
                mensagem = (
                    f"IFB - Registro disciplinar envolvendo {estudantes_info} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Consulte o email {texto_email} para detalhes."
                )

            print(f"\n Mensagem: {mensagem}")

            # Enviar via Twilio
            print(f"\n Enviando SMS via Twilio...")
            ServicoNotificacao._enviar_sms_via_twilio('+5561993351183', mensagem)

        except Exception as e:
            print(f"\n ERRO ao enviar SMS:")
            print(f"   {str(e)}")
            logger.error(f" Erro ao enviar SMS para {responsavel.nome}: {str(e)}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def _enviar_sms_via_twilio(numero, mensagem):
        """Envia SMS via Twilio"""
        print(f"\n{'=' * 60}")
        print(f" _enviar_sms_via_twilio")
        print(f"{'=' * 60}")
        print(f" Número: {numero}")
        print(f" Mensagem: {mensagem}")

        try:
            if not hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                print("  Twilio não configurado - settings.TWILIO_ACCOUNT_SID não existe")
                return

            print(f"\n Importando Twilio Client...")
            from twilio.rest import Client

            print(f" Criando cliente Twilio...")
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            print(f"    Cliente criado")

            print(f"\n Enviando mensagem...")
            print(f"   De: {settings.TWILIO_PHONE_NUMBER}")
            print(f"   Para: {numero}")

            message = client.messages.create(
                body=mensagem,
                from_=settings.TWILIO_PHONE_NUMBER,
                to='+5561981564098'#numero
            )

            print(f"    SMS enviado com SUCESSO!")
            print(f"   SID: {message.sid}")
            print(f"   Status: {message.status}")

            logger.info(f" SMS Twilio enviado para {numero}: {message.sid}")

        except Exception as e:
            print(f"\n ERRO FATAL no Twilio:")
            print(f"   {str(e)}")
            logger.error(f" Erro Twilio: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def notificar_nova_ocorrencia(ocorrencia):
        """Notifica comissão sobre nova ocorrência"""
        print(f"\n{'=' * 60}")
        print(f" NOTIFICANDO COMISSÃO")
        print(f"{'=' * 60}")

        from .models import Servidor

        membros_comissao = Servidor.objects.filter(membro_comissao_disciplinar=True)
        print(f" Membros da comissão: {membros_comissao.count()}")

        for servidor in membros_comissao:
            print(f"\n Notificando: {servidor.nome}")

            prioridade = 'ALTA' if (
                    ocorrencia.infracao and
                    ocorrencia.infracao.gravidade in ['GRAVE', 'GRAVISSIMA']
            ) else 'MEDIA'

            print(f"   Prioridade: {prioridade}")

            try:
                ServicoNotificacao.criar_notificacao(
                    usuario=servidor.user,
                    tipo='NOVA_OCORRENCIA',
                    titulo=f'Nova Ocorrência #{ocorrencia.id}',
                    mensagem=f'Registrada por {ocorrencia.responsavel_registro.nome}',
                    ocorrencia=ocorrencia,
                    prioridade=prioridade
                )
                print(f"    Notificação criada")
            except Exception as e:
                print(f"    ERRO: {str(e)}")

    @staticmethod
    def criar_notificacao(usuario, tipo, titulo, mensagem, ocorrencia=None, prioridade='MEDIA'):
        """Cria notificação in-app"""
        print(f"\n Criando notificação in-app...")
        print(f"   Usuário: {usuario.username}")
        print(f"   Tipo: {tipo}")
        print(f"   Título: {titulo}")

        notificacao = Notificacao.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            ocorrencia=ocorrencia,
            prioridade=prioridade
        )
        print(f"    Notificação #{notificacao.id} criada")

        if prioridade in ['ALTA', 'URGENTE']:
            print(f"    Enviando email (prioridade {prioridade})...")
            ServicoNotificacao.enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia)

        return notificacao

    @staticmethod
    def enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia=None):
        """Envia notificação por email"""
        print(f"\n Enviando notificação email...")
        print(f"   Para: {usuario.email}")

        try:
            preferencias = PreferenciaNotificacao.objects.get(usuario=usuario)
            if not preferencias.receber_notificacoes_urgentes:
                print(f"     Usuário desativou notificações urgentes")
                return
        except PreferenciaNotificacao.DoesNotExist:
            print(f"     Criando preferências padrão")
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
                'marcos.rodrigues@ifb.edu.br'#[usuario.email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            email.send()
            print(f"    Email enviado para {usuario.email}")
            logger.info(f" Email enviado para {usuario.email}")
        except Exception as e:
            print(f"    ERRO: {str(e)}")
            logger.error(f" Erro ao enviar email: {e}")