# test_email.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.conf import settings


def test_password_reset_email():
    context = {
        'protocol': 'http',
        'domain': 'localhost:8000',
        'uid': 'teste123',
        'token': 'token-teste',
    }

    subject = 'TESTE - Redefinição de Senha - Sistema de Ocorrências IFB'
    body_text = 'Versão em texto simples do email de redefinição'
    body_html = loader.render_to_string('registration/password_reset_email.html', context)

    email = EmailMultiAlternatives(
        subject,
        body_text,
        settings.DEFAULT_FROM_EMAIL,
        ['seu-email@teste.com']  # Coloque seu email real aqui
    )
    email.attach_alternative(body_html, "text/html")

    try:
        email.send()
        print("✅ Email de teste ENVIADO com SUCESSO!")
        print("📧 Verifique sua caixa de entrada e spam")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {str(e)}")


if __name__ == "__main__":
    test_password_reset_email()