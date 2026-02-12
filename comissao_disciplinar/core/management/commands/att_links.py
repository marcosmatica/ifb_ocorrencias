import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Estudante  # Certifique-se de que o nome do modelo está correto

class Command(BaseCommand):
    help = 'Confere e atualiza os links das fotos dos estudantes com base em um CSV'

    def handle(self, *args, **options):
        # 1. Localiza o arquivo no mesmo diretório do script
        file_path = Path(__file__).parent / 'upload_fotos.csv'

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado em: {file_path}"))
            return

        # 2. Leitura do arquivo
        # Nota: CSVs nativos não têm 'abas', mas o pandas trata o arquivo de forma robusta.
        # Se for um Excel renomeado para.csv, o sheet_name funcionará.
        try:
            # Tentamos ler como Excel primeiro por causa da menção a 'Planilha1'
            df = pd.read_excel(file_path, sheet_name='Planilha1', dtype={'matricula': str})
        except Exception:
            # Caso seja um CSV real (texto plano), lemos como CSV
            df = pd.read_csv(file_path, dtype={'matricula': str})

        self.stdout.write(f"Processando {len(df)} registros...")

        # 3. Otimização: Carregar estudantes do banco em um dicionário para busca rápida O(1)
        matriculas_csv = df['matricula'].tolist()
        estudantes_db = Estudante.objects.filter(matricula_sga__in=matriculas_csv)
        mapping = {obj.matricula_sga: obj for obj in estudantes_db}

        atualizados = 0
        inalterados = 0
        nao_encontrados = 0
        objetos_para_update = []

        # 4. Comparação e Identificação de mudanças
        for _, row in df.iterrows():
            matricula = str(row['matricula']).strip()
            novo_link = str(row['link_foto']).strip()

            estudante = mapping.get(matricula)

            if estudante:
                # Verifica se a URL cadastrada é diferente da que está na planilha
                if estudante.foto_url!= novo_link:
                    estudante.foto_url = novo_link
                    objetos_para_update.append(estudante)
                    atualizados += 1
                else:
                    inalterados += 1
            else:
                nao_encontrados += 1

        # 5. Persistência em massa (Bulk Update) para performance
        if objetos_para_update:
            with transaction.atomic():
                # Atualiza apenas o campo 'foto_url' de todos os objetos alterados de uma vez
                Estudante.objects.bulk_update(objetos_para_update, ['foto_url'])

        # 6. Relatório final
        self.stdout.write(self.style.SUCCESS(f"Sincronização concluída!"))
        self.stdout.write(f"- Atualizados: {atualizados}")
        self.stdout.write(f"- Já estavam corretos: {inalterados}")
        if nao_encontrados > 0:
            self.stdout.write(self.style.WARNING(f"- Matrículas não encontradas no sistema: {nao_encontrados}"))