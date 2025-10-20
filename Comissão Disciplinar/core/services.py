from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notificacao, PreferenciaNotificacao


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
            # Criar preferências padrão se não existirem
            PreferenciaNotificacao.objects.create(usuario=usuario)

        assunto = f"[Sistema Ocorrências] {titulo}"

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