# debug_email.py
import os
import django
from django.conf import settings

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.template import loader


def debug_specific_user():
    """Testa o envio para um usuário específico"""
    User = get_user_model()

    try:
        # Substitua pelo email que você está testando
        user = User.objects.get(email='3353645@etfbsb.edu.br')
        print(f"👤 Usuário: {user.username} ({user.email})")

        # Gerar token e UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        print(f"🔑 Token: {token}")
        print(f"🆔 UID: {uid}")

        context = {
            'protocol': 'http',
            'domain': 'localhost:8000',
            'uid': uid,
            'token': token,
            'user': user,
        }

        subject = 'DEBUG - Redefinição de Senha - Sistema de Ocorrências IFB'
        body_text = loader.render_to_string('registration/password_reset_email.txt', context)
        body_html = loader.render_to_string('registration/password_reset_email.html', context)

        print(f"📄 Template HTML: {len(body_html)} caracteres")

        email_msg = EmailMultiAlternatives(
            subject,
            body_text,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email_msg.attach_alternative(body_html, "text/html")

        # ENVIAR
        email_msg.send()
        print(f"✅ Email DEBUG enviado para {user.email}")

    except User.DoesNotExist:
        print("❌ Usuário não encontrado")
    except Exception as e:
        print(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    debug_specific_user()