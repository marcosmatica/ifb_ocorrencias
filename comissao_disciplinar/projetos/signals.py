from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Projeto, AlertaRelatorio


@receiver(post_save, sender=Projeto)
def calcular_proximo_relatorio_signal(sender, instance, created, **kwargs):
    """Calcula próximo relatório ao criar projeto"""
    if created and instance.data_inicio and not instance.proximo_relatorio:
        instance.calcular_proximo_relatorio()
        instance.save()


@receiver(post_save, sender=AlertaRelatorio)
def enviar_email_alerta_signal(sender, instance, created, **kwargs):
    """Envia e-mail quando alerta é criado"""
    if created and not instance.visualizado:
        projeto = instance.projeto
        coordenador = projeto.coordenador

        if instance.tipo == 'VENCIDO':
            assunto = f'⚠️ Relatório VENCIDO - {projeto.titulo}'
            mensagem = (
                f'Prezado(a) {coordenador.nome},\n\n'
                f'O relatório do projeto "{projeto.titulo}" está VENCIDO desde '
                f'{projeto.proximo_relatorio.strftime("%d/%m/%Y")}.\n\n'
                f'Processo: {projeto.numero_processo}\n\n'
                f'Acesse o sistema para mais detalhes.'
            )
        else:  # PROXIMO
            dias = (projeto.proximo_relatorio - instance.data_alerta).days
            assunto = f'📅 Lembrete: Relatório próximo - {projeto.titulo}'
            mensagem = (
                f'Prezado(a) {coordenador.nome},\n\n'
                f'O relatório do projeto "{projeto.titulo}" vence em {dias} dias '
                f'({projeto.proximo_relatorio.strftime("%d/%m/%Y")}).\n\n'
                f'Processo: {projeto.numero_processo}\n\n'
                f'Acesse o sistema para mais detalhes.'
            )

        try:
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [coordenador.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f'Erro ao enviar e-mail de alerta: {e}')