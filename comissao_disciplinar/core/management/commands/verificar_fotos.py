from django.core.management.base import BaseCommand
from core.models import Estudante
import os

class Command(BaseCommand):
    help = 'Verifica o status das fotos dos estudantes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detalhado',
            action='store_true',
            help='Mostra listagem detalhada de cada estudante',
        )

    def handle(self, *args, **options):
        estudantes = Estudante.objects.all().order_by('matricula_sga')
        detalhado = options['detalhado']
        
        total = estudantes.count()
        com_foto_local = 0
        com_foto_drive = 0
        com_ambas = 0
        sem_foto = 0
        foto_local_invalida = 0
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("📸 VERIFICAÇÃO DE FOTOS DOS ESTUDANTES"))
        self.stdout.write("="*70 + "\n")
        
        for estudante in estudantes:
            tem_local = False
            tem_drive = False
            local_valido = False
            
            # Verificar foto local
            if estudante.foto:
                try:
                    if os.path.exists(estudante.foto.path):
                        tem_local = True
                        local_valido = True
                except:
                    tem_local = True  # Cadastrada mas inválida
                    local_valido = False
            
            # Verificar foto Drive
            if estudante.foto_url:
                tem_drive = True
            
            # Contabilizar
            if tem_local and local_valido and tem_drive:
                com_ambas += 1
            elif tem_local and local_valido:
                com_foto_local += 1
            elif tem_drive:
                com_foto_drive += 1
            elif not tem_local and not tem_drive:
                sem_foto += 1
            
            # Verificar fotos locais inválidas
            if tem_local and not local_valido:
                foto_local_invalida += 1
                if detalhado:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  [{estudante.matricula_sga}] {estudante.nome[:40]:40} - "
                            f"Foto local cadastrada mas arquivo não existe"
                        )
                    )
            
            # Mostrar detalhes se solicitado
            if detalhado:
                status = []
                if tem_local and local_valido:
                    status.append("✅ Local")
                elif tem_local:
                    status.append("⚠️ Local (inválida)")
                if tem_drive:
                    status.append("☁️ Drive")
                if not status:
                    status.append("❌ Sem foto")
                
                status_str = " | ".join(status)
                self.stdout.write(
                    f"  [{estudante.matricula_sga}] {estudante.nome[:40]:40} - {status_str}"
                )
        
        # Relatório
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("📊 RESUMO:"))
        self.stdout.write("="*70)
        self.stdout.write(f"Total de estudantes: {total}")
        self.stdout.write(self.style.SUCCESS(f"✅ Com foto local válida: {com_foto_local}"))
        self.stdout.write(f"☁️  Apenas com foto Drive: {com_foto_drive}")
        self.stdout.write(f"✅☁️  Com ambas (local + Drive): {com_ambas}")
        self.stdout.write(self.style.ERROR(f"❌ Sem foto: {sem_foto}"))
        self.stdout.write(self.style.WARNING(f"⚠️  Foto local inválida: {foto_local_invalida}"))
        self.stdout.write("="*70)
        
        # Percentuais
        if total > 0:
            self.stdout.write("\n" + self.style.SUCCESS("📈 PERCENTUAIS:"))
            self.stdout.write("-"*70)
            
            total_com_foto = total - sem_foto
            total_local = com_foto_local + com_ambas
            total_drive = com_foto_drive + com_ambas
            
            self.stdout.write(
                f"Cobertura total de fotos: "
                f"{(total_com_foto / total * 100):.1f}% ({total_com_foto}/{total})"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fotos locais disponíveis: "
                    f"{(total_local / total * 100):.1f}% ({total_local}/{total})"
                )
            )
            self.stdout.write(
                f"Fotos Drive disponíveis: "
                f"{(total_drive / total * 100):.1f}% ({total_drive}/{total})"
            )
            
            if total_local > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Sistema usando prioritariamente fotos locais: "
                        f"{(total_local / total_com_foto * 100):.1f}% dos que têm foto"
                    )
                )
            
            self.stdout.write("="*70 + "\n")
        
        # Recomendações
        if foto_local_invalida > 0:
            self.stdout.write(self.style.WARNING("\n⚠️  ATENÇÃO:"))
            self.stdout.write(
                f"Existem {foto_local_invalida} registros com referência a foto local "
                "mas o arquivo não existe."
            )
            self.stdout.write(
                "Execute: python manage.py limpar_fotos_invalidas "
                "para corrigir.\n"
            )
        
        if com_foto_drive > 0 and com_foto_local < total:
            self.stdout.write(self.style.WARNING("💡 SUGESTÃO:"))
            self.stdout.write(
                f"Existem {com_foto_drive} fotos apenas no Drive. "
                "Para melhor performance:"
            )
            self.stdout.write(
                "Execute: python manage.py migrar_fotos_drive "
                "para baixá-las localmente.\n"
            )