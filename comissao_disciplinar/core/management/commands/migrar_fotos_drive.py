from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from core.models import Estudante
import requests
import re
import os
import time

class Command(BaseCommand):
    help = 'Baixa fotos do Google Drive para armazenamento local'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula sem baixar',
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Número máximo de fotos para baixar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limite = options['limite']
        
        # Filtrar estudantes que têm foto_url mas não têm foto local válida
        query = Estudante.objects.filter(
            foto_url__isnull=False
        ).exclude(foto_url='')
        
        # Remover os que já têm foto local válida
        estudantes_para_migrar = []
        for est in query:
            if est.foto:
                try:
                    if os.path.exists(est.foto.path):
                        continue  # Já tem foto local
                except:
                    pass
            estudantes_para_migrar.append(est)
        
        total = len(estudantes_para_migrar)
        if limite:
            estudantes_para_migrar = estudantes_para_migrar[:limite]
            total = min(total, limite)
        
        baixados = 0
        erros = 0
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(
            self.style.SUCCESS("📥 MIGRAÇÃO DE FOTOS: Google Drive → Local")
        )
        self.stdout.write("="*70 + "\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 MODO DRY-RUN ATIVADO (sem download)\n"))
        
        if limite:
            self.stdout.write(f"📊 Limite: {limite} fotos\n")
        
        self.stdout.write(f"📋 Total para processar: {total}\n")
        self.stdout.write("-"*70 + "\n")
        
        for i, estudante in enumerate(estudantes_para_migrar, 1):
            # Extrair ID do Drive
            match = re.search(r'id=([a-zA-Z0-9_-]+)', estudante.foto_url)
            if not match:
                self.stdout.write(
                    self.style.ERROR(
                        f"[{i:3}/{total}] ❌ {estudante.matricula_sga:12} - "
                        f"URL inválida"
                    )
                )
                erros += 1
                continue
            
            file_id = match.group(1)
            
            # Tentar diferentes URLs do Google Drive
            urls = [
                f'https://drive.google.com/uc?export=download&id={file_id}',
                f'https://drive.google.com/thumbnail?id={file_id}&sz=w800',
            ]
            
            if dry_run:
                self.stdout.write(
                    f"[{i:3}/{total}] 🔍 {estudante.matricula_sga:12} - "
                    f"{estudante.nome[:30]:30} - Simulado"
                )
                continue
            
            # Tentar baixar
            sucesso = False
            for url_idx, url in enumerate(urls):
                try:
                    response = requests.get(url, timeout=30, allow_redirects=True)
                    
                    if response.status_code == 200 and len(response.content) > 1000:
                        # Determinar extensão baseado no content-type
                        content_type = response.headers.get('Content-Type', '').lower()
                        ext = '.jpg'
                        
                        if 'png' in content_type:
                            ext = '.png'
                        elif 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'
                        elif 'webp' in content_type:
                            ext = '.webp'
                        
                        # Nome do arquivo: matricula + extensão
                        filename = f"{estudante.matricula_sga}{ext}"
                        
                        # Salvar
                        estudante.foto.save(
                            filename,
                            ContentFile(response.content),
                            save=True
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[{i:3}/{total}] ✅ {estudante.matricula_sga:12} - "
                                f"{estudante.nome[:30]:30} - "
                                f"{len(response.content)/1024:.1f}KB"
                            )
                        )
                        baixados += 1
                        sucesso = True
                        
                        # Pequeno delay para não sobrecarregar
                        time.sleep(0.5)
                        break
                        
                    elif url_idx == len(urls) - 1:
                        # Última URL também falhou
                        self.stdout.write(
                            self.style.ERROR(
                                f"[{i:3}/{total}] ❌ {estudante.matricula_sga:12} - "
                                f"{estudante.nome[:30]:30} - "
                                f"Status {response.status_code}"
                            )
                        )
                        erros += 1
                        
                except requests.exceptions.Timeout:
                    if url_idx == len(urls) - 1:
                        self.stdout.write(
                            self.style.ERROR(
                                f"[{i:3}/{total}] ⏱️  {estudante.matricula_sga:12} - "
                                f"{estudante.nome[:30]:30} - Timeout"
                            )
                        )
                        erros += 1
                        
                except Exception as e:
                    if url_idx == len(urls) - 1:
                        self.stdout.write(
                            self.style.ERROR(
                                f"[{i:3}/{total}] ❌ {estudante.matricula_sga:12} - "
                                f"{estudante.nome[:30]:30} - {str(e)[:20]}"
                            )
                        )
                        erros += 1
        
        # Resumo
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("📊 RESUMO:"))
        self.stdout.write("="*70)
        
        if not dry_run:
            self.stdout.write(f"Total processado: {total}")
            self.stdout.write(self.style.SUCCESS(f"✅ Baixados com sucesso: {baixados}"))
            self.stdout.write(self.style.ERROR(f"❌ Erros: {erros}"))
            
            if baixados > 0:
                taxa_sucesso = (baixados / total * 100)
                self.stdout.write(f"\n📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
        else:
            self.stdout.write(f"Fotos que seriam baixadas: {total}")
            self.stdout.write(
                self.style.WARNING(
                    "\nExecute sem --dry-run para baixar as fotos."
                )
            )
        
        self.stdout.write("="*70 + "\n")
        
        if not dry_run and baixados > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Migração concluída! {baixados} fotos agora estão "
                    "armazenadas localmente."
                )
            )
            self.stdout.write(
                "\n💡 Execute 'python manage.py verificar_fotos' "
                "para ver o status atualizado.\n"
            )