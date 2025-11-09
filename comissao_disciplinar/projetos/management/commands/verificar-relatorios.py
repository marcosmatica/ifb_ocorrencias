from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from projetos.models import Projeto, AlertaRelatorio


class Command(BaseCommand):
    help = 'Verifica projetos com relatórios pendentes e envia alertas'

    def handle(self, *args, **options):
        hoje = timezone.now().date()

        # Projetos ativos
        projetos_ativos = Projeto.objects.filter(situacao='ATIVO')

        alertas_criados = 0
        emails_enviados = 0

        for projeto in projetos_ativos:
            if not projeto.proximo_relatorio:
                continue

            # Relatório vencido
            if projeto.proximo_relatorio < hoje:
                # Criar alerta se não existe
                alerta, criado = AlertaRelatorio.objects.get_or_create(
                    projeto=projeto,
                    tipo='VENCIDO',
                    data_alerta=hoje,
                    defaults={'visualizado': False}
                )

                if criado:
                    alertas_criados += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Alerta VENCIDO: {projeto.titulo} - '
                            f'Prazo: {projeto.proximo_relatorio}'
                        )
                    )

                    # Enviar e-mail para coordenador
                    if self.enviar_email_alerta(projeto, 'vencido'):
                        emails_enviados += 1

            # Relatório próximo (7 dias)
            elif projeto.proximo_relatorio <= hoje + timedelta(days=7):
                alerta, criado = AlertaRelatorio.objects.get_or_create(
                    projeto=projeto,
                    tipo='PROXIMO',
                    data_alerta=hoje,
                    defaults={'visualizado': False}
                )

                if criado:
                    alertas_criados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Alerta PRÓXIMO: {projeto.titulo} - '
                            f'Prazo: {projeto.proximo_relatorio}'
                        )
                    )

                    # Enviar e-mail para coordenador
                    if self.enviar_email_alerta(projeto, 'proximo'):
                        emails_enviados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nResumo:\n'
                f'- Alertas criados: {alertas_criados}\n'
                f'- E-mails enviados: {emails_enviados}'
            )
        )

    def enviar_email_alerta(self, projeto, tipo):
        """Envia e-mail de alerta para coordenador do projeto"""
        try:
            if tipo == 'vencido':
                assunto = f'⚠️ Relatório VENCIDO - {projeto.titulo}'
                mensagem = f'''
                    Prezado(a) {projeto.coordenador.nome},
                    
                    O relatório do projeto "{projeto.titulo}" (Processo: {projeto.numero_processo}) 
                    está VENCIDO desde {projeto.proximo_relatorio.strftime("%d/%m/%Y")}.
                    
                    Por favor, providencie a entrega do relatório o mais rápido possível.
                    
                    Para'''
        except:
            pass