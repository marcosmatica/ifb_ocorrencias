from django.core.mail import send_mail
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import qrcode


def gerar_documento_pdf(ocorrencia, tipo_documento):
    """Gera documento PDF baseado no tipo"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Cabeçalho
    p.drawString(100, height - 100, "Instituto Federal de Brasília")
    p.drawString(100, height - 120, f"Documento: {tipo_documento}")

    # Conteúdo baseado no tipo
    y = height - 160

    if tipo_documento == 'REGISTRO':
        p.drawString(100, y, f"Registro de Ocorrência #{ocorrencia.id}")
        y -= 30
        p.drawString(100, y, f"Data: {ocorrencia.data}")
        y -= 20
        # Limitar tamanho da descrição
        descricao = ocorrencia.descricao[:100] + "..." if len(ocorrencia.descricao) > 100 else ocorrencia.descricao
        p.drawString(100, y, f"Descrição: {descricao}")

    elif tipo_documento == 'ATA_ADVERTENCIA':
        p.drawString(100, y, "ATA DE ADVERTÊNCIA")
        y -= 30
        estudantes = ", ".join([e.nome for e in ocorrencia.estudantes.all()])
        p.drawString(100, y, f"Estudante(s): {estudantes}")

    # Gerar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"https://ifb.edu.br/ocorrencias/{ocorrencia.id}/verificar")
    qr.make(fit=True)

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer


def enviar_notificacao_email_sincrono(notificacao_id):
    """Envio síncrono de notificações por e-mail (sem Celery)"""
    from .models import NotificacaoOficial

    try:
        notificacao = NotificacaoOficial.objects.get(id=notificacao_id)
        destinatarios = [email.strip() for email in notificacao.destinatarios.split(',')]

        send_mail(
            subject=f"IFB - {notificacao.get_tipo_display()}",
            message=notificacao.texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )

        return f"E-mail enviado para {len(destinatarios)} destinatário(s)"
    except Exception as e:
        return f"Erro ao enviar e-mail: {str(e)}"