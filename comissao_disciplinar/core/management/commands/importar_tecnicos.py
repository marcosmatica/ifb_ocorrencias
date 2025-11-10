# core/management/commands/importar_tecnicos.py
import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Servidor, Campus

class Command(BaseCommand):
    help = 'Importa técnicos educacionais do CSV para o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Caminho para o arquivo CSV com os dados dos técnicos'
        )
        parser.add_argument(
            '--campus_id',
            type=int,
            required=True,
            help='ID do campus padrão para todos os técnicos'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        campus_id = options['campus_id']

        # Verificar se o arquivo existe
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f'Arquivo não encontrado: {csv_file}')
            )
            return

        # Verificar se o campus existe
        try:
            campus = Campus.objects.get(id=campus_id)
        except Campus.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Campus com ID {campus_id} não encontrado')
            )
            return

        # Mapeamento das coordenações do CSV para as choices do modelo
        MAPEAMENTO_COORDENACOES = {
            'Coordenação Pedagógica': 'CDPD',
            'Coordenação de Registro Acadêmico': 'CDRA',
            'Direção de Ensino, Pesquisa e Extensão': 'DREP',
            'Coordenação Geral': 'CGEN',
            'Coordenação de Assistência Estudantil': 'CDAE',
            'Coordenação de Biblioteca': 'CDBA',
            'NAPNE': 'NAPNE',
            'Direção Geral': 'DG'
        }

        contadores = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0
        }

        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for linha in reader:
                try:
                    usuario_siape = linha['usuario']
                    nome = linha['Nome']
                    email = linha['email']
                    senha = linha['senha']
                    funcao = linha['funcao']
                    coordenacao_csv = linha['coordenacao']

                    # Converter booleanos do CSV
                    comissao_disciplinar = linha['comissao_disciplinar'].upper() == 'TRUE'
                    registrar_atendimento = linha['registrar_atendimento'].upper() == 'TRUE'
                    ficha_aluno = linha['ficha_aluno'].upper() == 'TRUE'

                    # Mapear coordenação
                    coordenacao_modelo = MAPEAMENTO_COORDENACOES.get(coordenacao_csv)
                    if not coordenacao_modelo:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Coordenação não mapeada: {coordenacao_csv} para usuário {usuario_siape}'
                            )
                        )
                        contadores['erros'] += 1
                        continue

                    # Criar ou atualizar usuário
                    user, user_created = User.objects.get_or_create(
                        username=usuario_siape,
                        defaults={
                            'email': email,
                            'first_name': nome.split()[0],
                            'last_name': ' '.join(nome.split()[1:]) if len(nome.split()) > 1 else '',
                        }
                    )

                    if user_created:
                        user.set_password(senha)
                        user.save()

                    # Criar ou atualizar servidor
                    servidor, servidor_created = Servidor.objects.update_or_create(
                        user=user,
                        defaults={
                            'siape': usuario_siape,
                            'nome': nome,
                            'funcao': funcao,
                            'email': email,
                            'campus': campus,
                            'coordenacao': coordenacao_modelo,
                            'membro_comissao_disciplinar': comissao_disciplinar,
                            'pode_registrar_atendimento': registrar_atendimento,
                            'pode_visualizar_ficha_aluno': ficha_aluno,
                        }
                    )

                    if servidor_created:
                        contadores['criados'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Criado: {nome} ({usuario_siape})')
                        )
                    else:
                        contadores['atualizados'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Atualizado: {nome} ({usuario_siape})')
                        )

                except Exception as e:
                    contadores['erros'] += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Erro ao processar linha {linha}: {str(e)}'
                        )
                    )

        # Resumo final
        self.stdout.write(
            self.style.SUCCESS(
                f'\n--- RESUMO DA IMPORTACAO ---\n'
                f'Criados: {contadores["criados"]}\n'
                f'Atualizados: {contadores["atualizados"]}\n'
                f'Erros: {contadores["erros"]}\n'
                f'Total processado: {contadores["criados"] + contadores["atualizados"] + contadores["erros"]}'
            )
        )