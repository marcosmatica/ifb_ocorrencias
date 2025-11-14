# core/management/commands/test_notifications.py
"""
Script para testar notificações

Uso:
    python manage.py test_notifications --email
    python manage.py test_notifications --sms
    python manage.py test_notifications --all
"""

from django.core.management.base import BaseCommand
from core.services import ServicoNotificacao
from core.models import Ocorrencia, OcorrenciaRapida, Responsavel
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Testa o sistema de notificações'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            action='store_true',
            help='Testar envio de email',
        )
        parser.add_argument(
            '--sms',
            action='store_true',
            help='Testar envio de SMS',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Testar email e SMS',
        )
        parser.add_argument(
            '--ocorrencia-id',
            type=int,
            help='ID da ocorrência para teste',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 Iniciando testes de notificação...'))

        # Determinar o que testar
        test_email = options['email'] or options['all']
        test_sms = options['sms'] or options['all']

        if not (test_email or test_sms):
            self.stdout.write(self.style.WARNING('⚠️ Especifique --email, --sms ou --all'))
            return

        # Buscar ocorrência para teste
        if options['ocorrencia_id']:
            try:
                ocorrencia = Ocorrencia.objects.get(id=options['ocorrencia_id'])
                tipo = 'ocorrencia'
            except Ocorrencia.DoesNotExist:
                try:
                    ocorrencia = OcorrenciaRapida.objects.get(id=options['ocorrencia_id'])
                    tipo = 'ocorrencia_rapida'
                except OcorrenciaRapida.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'❌ Ocorrência {options["ocorrencia_id"]} não encontrada'))
                    return
        else:
            # Usar primeira ocorrência disponível
            ocorrencia = Ocorrencia.objects.first() or OcorrenciaRapida.objects.first()
            tipo = 'ocorrencia' if isinstance(ocorrencia, Ocorrencia) else 'ocorrencia_rapida'

            if not ocorrencia:
                self.stdout.write(self.style.ERROR('❌ Nenhuma ocorrência encontrada no banco'))
                return

        self.stdout.write(f'📋 Usando ocorrência #{ocorrencia.id} ({tipo})')

        # Verificar responsáveis
        estudantes = ocorrencia.estudantes.all()
        if not estudantes:
            self.stdout.write(self.style.ERROR('❌ Ocorrência sem estudantes'))
            return

        total_responsaveis = sum(e.responsaveis.count() for e in estudantes)
        if total_responsaveis == 0:
            self.stdout.write(self.style.ERROR('❌ Nenhum responsável cadastrado'))
            return

        self.stdout.write(f'👥 Encontrados {total_responsaveis} responsáveis')

        # Executar testes
        if test_email:
            self.test_email_notification(ocorrencia, tipo)

        if test_sms:
            self.test_sms_notification(ocorrencia, tipo)

        self.stdout.write(self.style.SUCCESS('\n✅ Testes concluídos!'))

    def test_email_notification(self, ocorrencia, tipo):
        """Testa notificação por email"""
        self.stdout.write(self.style.HTTP_INFO('\n📧 Testando EMAIL...'))

        try:
            ServicoNotificacao.notificar_responsaveis_ocorrencia(ocorrencia, tipo)
            self.stdout.write(self.style.SUCCESS('✅ Emails enviados com sucesso'))
            self.stdout.write('   Verifique a caixa de entrada dos responsáveis')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao enviar email: {str(e)}'))

    def test_sms_notification(self, ocorrencia, tipo):
        """Testa notificação por SMS"""
        self.stdout.write(self.style.HTTP_INFO('\n📱 Testando SMS...'))

        estudantes = ocorrencia.estudantes.all()
        for estudante in estudantes:
            for responsavel in estudante.responsaveis.all():
                if responsavel.preferencia_contato in ['CELULAR', 'WHATSAPP']:
                    self.stdout.write(f'   Enviando para {responsavel.nome} ({responsavel.celular})')

                    try:
                        # Testar mensagem
                        mensagem = f"IFB - Teste de notificação para {estudante.nome}"

                        # Tentar Twilio
                        try:
                            ServicoNotificacao._enviar_sms_via_twilio(
                                responsavel.celular,
                                mensagem
                            )
                            self.stdout.write(self.style.SUCCESS('   ✅ SMS Twilio enviado'))
                        except Exception as e:
                            # Tentar Zenvia
                            try:
                                ServicoNotificacao._enviar_sms_via_zenvia(
                                    responsavel.celular,
                                    mensagem
                                )
                                self.stdout.write(self.style.SUCCESS('   ✅ SMS Zenvia enviado'))
                            except Exception as e2:
                                self.stdout.write(self.style.ERROR(f'   ❌ Erro: {str(e2)}'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ Erro geral: {str(e)}'))


# Script alternativo direto (sem Django command)
def test_notifications_simple():
    """
    Teste simples para executar no shell do Django

    Uso:
        python manage.py shell
        >>> from core.test_notifications import test_notifications_simple
        >>> test_notifications_simple()
    """
    from core.services import ServicoNotificacao
    from core.models import Ocorrencia

    print("🧪 Teste simples de notificações")

    # Buscar primeira ocorrência
    ocorrencia = Ocorrencia.objects.first()
    if not ocorrencia:
        print("❌ Nenhuma ocorrência encontrada")
        return

    print(f"📋 Usando ocorrência #{ocorrencia.id}")

    # Testar notificação
    try:
        ServicoNotificacao.notificar_responsaveis_ocorrencia(
            ocorrencia,
            tipo_ocorrencia='ocorrencia'
        )
        print("✅ Notificações enviadas!")
        print("📧 Verifique os emails")
        print("📱 Verifique os SMS (se configurado)")
    except Exception as e:
        print(f"❌ Erro: {str(e)}")


if __name__ == '__main__':
    # Permite executar direto com: python test_notifications.py
    import django
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comissao_disciplinar.settings')
    django.setup()

    test_notifications_simple()