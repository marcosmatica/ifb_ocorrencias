from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ocorrencia, NotificacaoOficial


@receiver(post_save, sender=Ocorrencia)
def ocorrencia_criada(sender, instance, created, **kwargs):
    """Ações automáticas quando uma ocorrência é criada"""
    if created:
        # Log de auditoria já é feito pelo django-auditlog
        pass


@receiver(post_save, sender=NotificacaoOficial)
def notificacao_enviada(sender, instance, created, **kwargs):
    """Registrar envio de notificação"""
    if created:
        # Aqui você pode adicionar lógica adicional
        # como enviar push notification, SMS, etc.
        pass