import csv
import os
import django
from django.db import transaction

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from pedagogico.models import Disciplina, DisciplinaTurma
from core.models import Turma, Curso, Servidor


def importar_disciplinas_csv(caminho_arquivo):
    """
    Importa disciplinas do CSV e as associa às turmas correspondentes
    """
    # Encontrar o coordenador Bruno Tardin
    try:
        coordenador = Servidor.objects.get(nome__icontains='Bruno oliveira Tardin')
    except Servidor.DoesNotExist:
        print("❌ Coordenador Bruno Tardin não encontrado!")
        return
    except Servidor.MultipleObjectsReturned:
        coordenador = Servidor.objects.filter(nome__icontains='Bruno Tardin').first()
        print(f"⚠️  Múltiplos Bruno Tardin encontrados. Usando: {coordenador.nome}")

    # Mapeamento de anos para cursos (ajuste conforme seus cursos)
    mapeamento_cursos = {
        '1': 'Técnico em Produção Audiovisual',
        '2': 'Técnico em Produção Audiovisual',
        '3': 'Técnico em Produção Audiovisual'
    }

    disciplinas_criadas = 0
    disciplinas_turma_criadas = 0

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        reader = csv.DictReader(arquivo)

        for linha in reader:
            turmas_str = linha['Ano/Turmas']
            nome_disciplina = linha['Disciplina'].strip()

            # Determinar bimestres ativos
            bimestres_ativos = []
            if linha['1Bim'].upper() == 'TRUE':
                bimestres_ativos.append('1')
            if linha['2Bim'].upper() == 'TRUE':
                bimestres_ativos.append('2')
            if linha['3Bim'].upper() == 'TRUE':
                bimestres_ativos.append('3')
            if linha['4Bim'].upper() == 'TRUE':
                bimestres_ativos.append('4')

            bimestres_str = ','.join(bimestres_ativos)

            # Extrair ano das turmas (primeiro caractere)
            ano = turmas_str[0]  # '1', '2' ou '3'

            # Encontrar curso correspondente
            try:
                curso_nome = mapeamento_cursos[ano]
                curso = Curso.objects.get(nome=curso_nome)
            except KeyError:
                print(f"❌ Ano não mapeado: {ano}")
                continue
            except Curso.DoesNotExist:
                print(f"❌ Curso não encontrado: {curso_nome}")
                continue

            # Criar código único para disciplina
            codigo = f"{curso.sigla if hasattr(curso, 'sigla') else curso.nome[:3]}-{nome_disciplina[:10].replace(' ', '').upper()}"

            # Criar ou atualizar disciplina
            disciplina, criada = Disciplina.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nome': nome_disciplina,
                    'curso': curso,
                    'carga_horaria': 80,  # Valor padrão, ajuste conforme necessário
                    'ementa': f"Ementa da disciplina {nome_disciplina}",
                    'bimestres_ativos': bimestres_str,
                    'ativa': True
                }
            )

            if criada:
                disciplinas_criadas += 1
                print(f"✅ Disciplina criada: {disciplina.nome}")
            else:
                # Atualizar bimestres se disciplina já existir
                disciplina.bimestres_ativos = bimestres_str
                disciplina.save()
                print(f"🔄 Disciplina atualizada: {disciplina.nome}")

            # Processar turmas (separadas por '-')
            turmas_lista = turmas_str.split('-')

            for turma_sigla in turmas_lista:
                turma_sigla = turma_sigla.strip()

                try:
                    # Encontrar turma pelo nome
                    turma = Turma.objects.get(nome=turma_sigla)

                    # Criar DisciplinaTurma para cada bimestre ativo
                    for bimestre in bimestres_ativos:
                        periodo = f"2025.{bimestre}"  # Ajuste o ano conforme necessário

                        disciplina_turma, dt_criada = DisciplinaTurma.objects.get_or_create(
                            disciplina=disciplina,
                            turma=turma,
                            periodo=periodo,
                            defaults={
                                'docente': None  # Define Bruno Tardin como docente inicial
                            }
                        )

                        if dt_criada:
                            disciplinas_turma_criadas += 1
                            print(f"  📚 Associada à turma {turma.nome} (período {periodo})")

                except Turma.DoesNotExist:
                    print(f"❌ Turma não encontrada: {turma_sigla}")
                    continue

    print(f"\n🎉 Importação concluída!")
    print(f"📝 Disciplinas criadas/atualizadas: {disciplinas_criadas}")
    print(f"🔗 Associações turma-disciplina: {disciplinas_turma_criadas}")


# Versão como comando management personalizado
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Importa disciplinas a partir de um arquivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'arquivo_csv',
            type=str,
            help='Caminho para o arquivo CSV com as disciplinas'
        )

    def handle(self, *args, **options):
        arquivo_csv = options['arquivo_csv']

        if not os.path.exists(arquivo_csv):
            self.stdout.write(
                self.style.ERROR(f'❌ Arquivo não encontrado: {arquivo_csv}')
            )
            return

        self.stdout.write(f'📖 Importando disciplinas de: {arquivo_csv}')

        try:
            with transaction.atomic():
                importar_disciplinas_csv(arquivo_csv)
                self.stdout.write(
                    self.style.SUCCESS('✅ Importação concluída com sucesso!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro durante a importação: {str(e)}')
            )
            raise


# Para executar diretamente (sem comando management)
if __name__ == "__main__":
    importar_disciplinas_csv('importar_turmas.csv')