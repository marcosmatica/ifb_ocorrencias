from django.core.management.base import BaseCommand
from django.core.files import File
from core.models import Estudante
import os
import re

class Command(BaseCommand):
    help = 'Migra fotos locais para o sistema e remove os arquivos processados'

    def add_arguments(self, parser):
        parser.add_argument('pasta', type=str, help='Caminho da pasta com as fotos')
        parser.add_argument('--dry-run', action='store_true', help='Simula sem alterar banco ou apagar arquivos')
        parser.add_argument('--sobrescrever', action='store_true', help='Sobrescreve fotos existentes no banco')

    def handle(self, *args, **options):
        pasta = options['pasta']
        dry_run = options['dry_run']
        sobrescrever = options['sobrescrever']

        if not os.path.exists(pasta):
            self.stdout.write(self.style.ERROR(f'❌ Pasta não encontrada: {pasta}'))
            return

        extensoes = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(extensoes)]

        total = len(arquivos)
        migradas = 0
        removidos_duplicados = 0
        nao_encontrados = 0
        erros = 0

        self.stdout.write(self.style.SUCCESS(f"\n📂 INICIANDO MIGRAÇÃO E LIMPEZA: {total} arquivos\n"))

        for i, arquivo in enumerate(sorted(arquivos), 1):
            caminho_origem = os.path.join(pasta, arquivo)
            
            # 1. Extrair matrícula (Regex ajustada para pegar números de 8 a 15 dígitos)
            match = re.search(r'(\d{8,15})', arquivo)
            if not match:
                continue

            matricula = match.group(1)

            # 2. Buscar estudante
            try:
                estudante = Estudante.objects.get(matricula_sga=matricula)
            except Estudante.DoesNotExist:
                nao_encontrados += 1
                continue
            except Exception:
                erros += 1
                continue

            # --- Lógica de Verificação e Exclusão ---

            # Caso A: Estudante já tem foto e não vamos sobrescrever
            if estudante.foto and not sobrescrever:
                if not dry_run:
                    os.remove(caminho_origem)
                
                self.stdout.write(f"[{i:3}/{total}] 🗑️  {matricula} - Foto já existia. Arquivo local excluído.")
                removidos_duplicados += 1
                continue

            # Caso B: Salvar nova foto (ou sobrescrever)
            if dry_run:
                self.stdout.write(f"[{i:3}/{total}] 🔍 {matricula} - Seria migrado e excluído.")
                continue

            try:
                with open(caminho_origem, 'rb') as f:
                    # O Django copia o arquivo para o storage (media/...)
                    estudante.foto.save(arquivo, File(f), save=True)
                
                # Após salvar com sucesso no banco/storage, exclui o original local
                os.remove(caminho_origem)
                
                self.stdout.write(
                    self.style.SUCCESS(f"[{i:3}/{total}] ✅ {matricula} - Migrado e arquivo local removido.")
                )
                migradas += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{i:3}/{total}] ❌ Erro ao processar {matricula}: {e}"))
                erros += 1

        # Resumo final
        self.stdout.write("\n" + "="*30)
        self.stdout.write(f"✅ Migrados: {migradas}")
        self.stdout.write(f"🗑️  Excluídos (já tinham foto): {removidos_duplicados}")
        self.stdout.write(f"⚠️  Não encontrados: {nao_encontrados}")
        self.stdout.write(f"❌ Erros: {erros}")
        self.stdout.write("="*30 + "\n")