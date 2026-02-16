import os
from PIL import Image


def otimizar_imagens(caminho_pasta, tamanho_max_kb=200):
    # Converte kb para bytes
    tamanho_max_bytes = tamanho_max_kb * 1024

    # Extensões permitidas
    extensoes = ('.jpg', '.jpeg', '.JPG', '.JPEG')

    # Percorre os arquivos da pasta
    for arquivo in os.listdir(caminho_pasta):
        if arquivo.endswith(extensoes):
            caminho_completo = os.path.join(caminho_pasta, arquivo)
            tamanho_atual = os.path.getsize(caminho_completo)
            print(tamanho_atual)

            if tamanho_atual > tamanho_max_bytes:
                print(f"Otimizando: {arquivo} ({tamanho_atual // 1024}kb)")

                qualidade = 95  # Qualidade inicial
                img = Image.open(caminho_completo)

                # Loop para reduzir a qualidade até atingir o tamanho alvo
                while tamanho_atual > tamanho_max_bytes and qualidade > 10:
                    print(qualidade)
                    # Salva temporariamente para verificar o novo tamanho
                    img.save(caminho_completo, "JPEG", optimize=True, quality=qualidade)
                    tamanho_atual = os.path.getsize(caminho_completo)
                    qualidade -= 5  # Reduz a qualidade em passos de 5

                print(f"--- Concluído: {arquivo} agora tem {tamanho_atual // 1024}kb (Qualidade: {qualidade})")
            else:
                print(f"Ignorado: {arquivo} já está abaixo de {tamanho_max_kb}kb")




if __name__ == '__main__':
    # --- CONFIGURAÇÃO ---
    pasta_das_fotos = r'C:\Users\matemarcos\Downloads\Arquivos_Baixados_16-02-2026_0724-20260216T103325Z-1-001\Arquivos_Baixados_16-02-2026_0724'  # Use 'r' antes das aspas no Windows
    otimizar_imagens(pasta_das_fotos)