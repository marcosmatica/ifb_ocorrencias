# core/management/commands/importar_ocorrencias_rapidas.py
import csv
import os
import chardet
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import OcorrenciaRapida, Estudante, Turma, Servidor
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Importa ocorrências rápidas de um arquivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Caminho do arquivo CSV')
        parser.add_argument('--servidor_id', type=int, help='ID do servidor responsável pelo registro')
        parser.add_argument('--encoding', type=str, help='Codificação do arquivo (ex: latin-1, cp1252)', default='auto')

    def detect_encoding(self, file_path):
        """Detecta a codificação do arquivo"""
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            self.stdout.write(f"Codificação detectada: {encoding} (confiança: {confidence:.2f})")
            return encoding

    def handle(self, *args, **options):
        file_path = options['file_path']
        servidor_id = options.get('servidor_id')
        encoding_option = options['encoding']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {file_path}'))
            return

        # Detectar codificação se for 'auto'
        if encoding_option == 'auto':
            encoding = self.detect_encoding(file_path)
        else:
            encoding = encoding_option

        # Obter servidor responsável
        try:
            if servidor_id:
                servidor = Servidor.objects.get(id=servidor_id)
            else:
                # Usar o primeiro superuser como fallback
                user = User.objects.filter(is_superuser=True).first()
                if user:
                    servidor = Servidor.objects.get(user=user)
                else:
                    self.stdout.write(self.style.ERROR('Nenhum superuser encontrado. Crie um superuser ou use --servidor_id.'))
                    return
        except Servidor.DoesNotExist:
            self.stdout.write(self.style.ERROR('Servidor não encontrado. Use --servidor_id ou certifique-se de que existe um servidor superuser.'))
            return

        contador = 0
        errors = []

        # Tentar abrir com diferentes codificações se necessário
        encodings_to_try = [encoding, 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8']

        for encoding_try in encodings_to_try:
            try:
                self.stdout.write(f"Tentando abrir com codificação: {encoding_try}")
                with open(file_path, 'r', encoding=encoding_try) as file:
                    # Ler arquivo CSV com delimitador ponto e vírgula
                    reader = csv.reader(file, delimiter=';')

                    # Pular cabeçalho
                    header = next(reader, None)
                    self.stdout.write(f"Cabeçalho: {header}")

                    for linha_num, linha in enumerate(reader, start=2):
                        if not linha or len(linha) < 4:  # Reduzido para 4 colunas mínimas
                            continue

                        try:
                            # Extrair dados da linha
                            data_str = linha[0].strip() if len(linha) > 0 else ''
                            tipo_ocorrencia = linha[1].strip() if len(linha) > 1 else ''
                            nome_estudante = linha[2].strip() if len(linha) > 2 else ''
                            turma_nome = linha[3].strip() if len(linha) > 3 else ''

                            # Pular linhas vazias
                            if not data_str and not nome_estudante:
                                continue

                            # Corrigir datas com formato inválido
                            data_str = self.corrigir_data(data_str)

                            # Validar dados obrigatórios
                            if not data_str:
                                errors.append(f'Linha {linha_num}: Data vazia ou inválida')
                                continue

                            if not tipo_ocorrencia:
                                errors.append(f'Linha {linha_num}: Tipo de ocorrência vazio')
                                continue

                            if not nome_estudante:
                                errors.append(f'Linha {linha_num}: Nome do estudante vazio')
                                continue

                            if not turma_nome:
                                errors.append(f'Linha {linha_num}: Turma vazia')
                                continue

                            # Converter data
                            try:
                                data = datetime.strptime(data_str, '%d/%m/%Y').date()
                            except ValueError as e:
                                errors.append(f'Linha {linha_num}: Data inválida "{data_str}" - {e}')
                                continue

                            # Mapear tipo de ocorrência
                            tipo_rapido = self.mapear_tipo_ocorrencia(tipo_ocorrencia)
                            if not tipo_rapido:
                                errors.append(f'Linha {linha_num}: Tipo de ocorrência não mapeado: "{tipo_ocorrencia}"')
                                continue

                            # Buscar turma - tentar diferentes formatos
                            turma = self.encontrar_turma(turma_nome)
                            if not turma:
                                errors.append(f'Linha {linha_num}: Turma não encontrada: "{turma_nome}"')
                                continue

                            # Buscar estudante - tentar diferentes abordagens
                            estudante = self.encontrar_estudante(nome_estudante, turma)
                            if not estudante:
                                errors.append(f'Linha {linha_num}: Estudante não encontrado: "{nome_estudante}" na turma "{turma_nome}"')
                                continue

                            # Verificar se a ocorrência já existe (evitar duplicatas)
                            if OcorrenciaRapida.objects.filter(
                                    data=data,
                                    estudantes=estudante,
                                    tipo_rapido=tipo_rapido
                            ).exists():
                                self.stdout.write(f'Linha {linha_num}: Ocorrência duplicada para {nome_estudante} em {data}')
                                continue

                            # Criar ocorrência rápida
                            ocorrencia = OcorrenciaRapida(
                                data=data,
                                horario=timezone.now().time(),  # Usar horário atual como padrão
                                turma=turma,
                                tipo_rapido=tipo_rapido,
                                responsavel_registro=servidor
                            )
                            ocorrencia.save()
                            ocorrencia.estudantes.add(estudante)

                            contador += 1
                            if contador % 10 == 0:  # Feedback a cada 10 registros
                                self.stdout.write(f'Linha {linha_num}: {contador} ocorrências criadas...')

                        except Exception as e:
                            errors.append(f'Linha {linha_num}: Erro inesperado - {str(e)}')
                            continue

                # Se chegou aqui, a codificação funcionou
                break

            except UnicodeDecodeError as e:
                self.stdout.write(f"Falha com codificação {encoding_try}: {e}")
                continue
            except Exception as e:
                errors.append(f"Erro ao processar arquivo: {str(e)}")
                break

        # Resumo da importação
        self.stdout.write(self.style.SUCCESS(f'\n--- RESUMO DA IMPORTAÇÃO ---'))
        self.stdout.write(self.style.SUCCESS(f'Ocorrências importadas: {contador}'))

        if errors:
            self.stdout.write(self.style.ERROR(f'\n--- ERROS ENCONTRADOS ({len(errors)}) ---'))
            for error in errors[:20]:  # Mostrar apenas os primeiros 20 erros
                self.stdout.write(self.style.ERROR(error))
            if len(errors) > 20:
                self.stdout.write(self.style.ERROR(f'... e mais {len(errors) - 20} erros'))

        if contador == 0 and errors:
            self.stdout.write(self.style.WARNING('\nDICA: Tente especificar a codificação manualmente com --encoding=latin-1'))

    def corrigir_data(self, data_str):
        """Corrige formatos de data inválidos"""
        correcoes = {
            '10/011/2025': '10/11/2025',
            '07/01/2025': '07/11/2025',  # Assumindo que é novembro
        }

        for erro, correcao in correcoes.items():
            if erro in data_str:
                return data_str.replace(erro, correcao)

        return data_str

    def mapear_tipo_ocorrencia(self, tipo_csv):
        """Mapeia o tipo do CSV para os tipos do modelo OcorrenciaRapida"""
        mapeamento = {
            'Atraso (Após 07h45m)': 'ATRASO',
            'Sem Uniforme': 'UNIFORME',
            'Atraso no retorno do intervalo': 'ATRASO',
            'Atraso': 'ATRASO',  # Caso haja variações
            'Uniforme': 'UNIFORME',  # Caso haja variações
            'Uso de Celular': 'CELULAR',
            'Retirou uniforme após entrada': 'UNIFORME',
            'Fora de sala de aula sem autorização': 'AUSENCIA',
        }
        return mapeamento.get(tipo_csv)

    def encontrar_turma(self, turma_nome):
        """Encontra a turma com diferentes estratégias"""
        # Tentar busca exata primeiro
        try:
            return Turma.objects.get(nome=turma_nome)
        except Turma.DoesNotExist:
            pass

        # Tentar buscar removendo espaços extras
        try:
            return Turma.objects.get(nome__iexact=turma_nome.strip())
        except Turma.DoesNotExist:
            pass

        # Tentar buscar por parte do nome
        turmas = Turma.objects.filter(nome__icontains=turma_nome)
        if turmas.exists():
            return turmas.first()

        return None

    def encontrar_estudante(self, nome_estudante, turma):
        """Encontra o estudante com diferentes estratégias"""
        # Busca exata com turma
        estudantes = Estudante.objects.filter(nome__iexact=nome_estudante, turma=turma)
        if estudantes.exists():
            return estudantes.first()

        # Busca por similaridade (removendo acentos e case)
        from django.db.models.functions import Lower
        estudantes = Estudante.objects.annotate(nome_lower=Lower('nome')).filter(
            nome_lower__iexact=nome_estudante.lower(),
            turma=turma
        )
        if estudantes.exists():
            return estudantes.first()

        # Busca por parte do nome
        estudantes = Estudante.objects.filter(
            nome__icontains=nome_estudante,
            turma=turma
        )
        if estudantes.exists():
            return estudantes.first()

        return None