# importar_fotos.py
import os
import sys
import csv
import django

# Configurar o ambiente Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from core.models import Estudante  # Ajuste 'core' para o nome do seu app

def detectar_encoding(caminho_arquivo):
    """
    Tenta detectar o encoding do arquivo
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    
    for encoding in encodings:
        try:
            with open(caminho_arquivo, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    
    return 'latin-1'  # fallback

def importar_links_fotos(caminho_arquivo):
    """
    Importa links de fotos de um arquivo CSV para os estudantes
    """
    try:
        # Detectar encoding
        encoding = detectar_encoding(caminho_arquivo)
        print(f"Detectado encoding: {encoding}")
        
        with open(caminho_arquivo, 'r', encoding=encoding) as arquivo:
            # Ler primeiras linhas para debug
            sample = arquivo.read(500)
            print(f"Primeiros caracteres do arquivo: {sample[:100]}...")
            arquivo.seek(0)  # Voltar ao início
            
            # Tentar detectar delimitador
            sniffed_dialect = csv.Sniffer().sniff(arquivo.read(1024))
            arquivo.seek(0)
            
            leitor = csv.DictReader(arquivo, delimiter=sniffed_dialect.delimiter)
            
            # Verificar se as colunas esperadas existem
            if 'Matricula' not in leitor.fieldnames or 'Link' not in leitor.fieldnames:
                print("Colunas encontradas:", leitor.fieldnames)
                raise ValueError("Colunas 'Matricula' ou 'Link foto' não encontradas no CSV")
            
            linhas_processadas = 0
            linhas_atualizadas = 0
            erros = []

            for linha in leitor:
                linhas_processadas += 1
                matricula = linha.get('Matricula', '').strip()
                link_foto = linha.get('Link', '').strip()

                if not matricula:
                    erros.append(f"Linha {linhas_processadas}: Matrícula vazia")
                    continue

                if not link_foto:
                    erros.append(f"Matrícula {matricula}: Link vazio")
                    continue

                try:
                    estudante = Estudante.objects.get(matricula_sga=matricula)
                    
                    # Atualizar apenas se o link for diferente
                    if estudante.foto_url != link_foto:
                        estudante.foto_url = link_foto
                        estudante.save()
                        linhas_atualizadas += 1
                        print(f"✓ Atualizado: {matricula} - {estudante.nome}")

                except Estudante.DoesNotExist:
                    erros.append(f"Matrícula não encontrada: {matricula}")
                except Exception as e:
                    erros.append(f"Erro na matrícula {matricula}: {str(e)}")

        # Resumo
        print(f"\n--- RESUMO DA IMPORTACAO ---")
        print(f"Linhas processadas: {linhas_processadas}")
        print(f"Estudantes atualizados: {linhas_atualizadas}")
        print(f"Erros: {len(erros)}")
        
        if erros:
            print(f"\n--- ERROS ENCONTRADOS ---")
            for erro in erros[:10]:  # Mostrar apenas os primeiros 10 erros
                print(erro)
            if len(erros) > 10:
                print(f"... e mais {len(erros) - 10} erros")

    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

def visualizar_csv(caminho_arquivo):
    """
    Função para visualizar o conteúdo do CSV e diagnosticar problemas
    """
    print(f"\n--- DIAGNÓSTICO DO ARQUIVO: {caminho_arquivo} ---")
    
    try:
        encoding = detectar_encoding(caminho_arquivo)
        print(f"Encoding detectado: {encoding}")
        
        with open(caminho_arquivo, 'r', encoding=encoding) as f:
            content = f.read()
            print(f"Tamanho do arquivo: {len(content)} caracteres")
            print(f"Primeiras 200 caracteres: {repr(content[:200])}")
            
            # Voltar ao início e ler como CSV
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(f.read(1000))
                f.seek(0)
                print(f"Delimitador detectado: {repr(dialect.delimiter)}")
                
                reader = csv.reader(f, dialect)
                headers = next(reader)
                print(f"Cabeçalhos: {headers}")
                
                print("\nPrimeiras 3 linhas de dados:")
                for i, row in enumerate(reader):
                    if i >= 3:
                        break
                    print(f"Linha {i+1}: {row}")
                    
            except csv.Error as e:
                print(f"Erro ao ler CSV: {e}")
                
    except Exception as e:
        print(f"Erro no diagnóstico: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python importar_fotos.py <caminho_do_arquivo_csv>")
        print("\nOpções:")
        print("  python importar_fotos.py links_fotos.csv    # Importar fotos")
        print("  python importar_fotos.py --diagnostico links_fotos.csv  # Diagnóstico do arquivo")
        sys.exit(1)
    
    caminho_csv = sys.argv[1]
    
    if caminho_csv == '--diagnostico' and len(sys.argv) == 3:
        visualizar_csv(sys.argv[2])
    elif caminho_csv == '--diagnostico':
        print("Uso: python importar_fotos.py --diagnostico <arquivo>")
    else:
        # Primeiro fazer diagnóstico
        visualizar_csv(caminho_csv)
        print("\n" + "="*50)
        print("INICIANDO IMPORTACAO...")
        print("="*50)
        importar_links_fotos(caminho_csv)