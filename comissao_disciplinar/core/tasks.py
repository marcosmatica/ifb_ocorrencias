# core/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import NotificacaoOficial


@shared_task
def enviar_notificacao_email(notificacao_id):
    try:
        notificacao = NotificacaoOficial.objects.get(id=notificacao_id)

        assunto = f"IFB - {notificacao.get_tipo_display()}"

        # Template de e-mail (crie em templates/emails/notificacao.html)
        html_message = render_to_string('emails/notificacao.html', {
            'notificacao': notificacao,
        })
        plain_message = strip_tags(html_message)

        # Enviar para cada destinatário
        destinatarios = [email.strip() for email in notificacao.destinatarios.split(',')]

        send_mail(
            assunto,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            destinatarios,
            html_message=html_message,
            fail_silently=False,
        )

        # Marcar como enviado
        notificacao.data_recebimento = timezone.now()
        notificacao.save()

        return f"E-mail enviado para {len(destinatarios)} destinatários"

    except Exception as e:
        # Log do erro
        print(f"Erro ao enviar e-mail: {str(e)}")
        raise e