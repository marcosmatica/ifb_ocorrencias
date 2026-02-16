import os
import sqlite3


def atualizar_fotos_sqlite(caminho_pasta_fotos, caminho_db='db.sqlite3'):
    # Conecta ao banco de dados SQLite
    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Erro ao abrir o banco de dados: {e}")
        return

    # Extensões permitidas
    extensoes = ('.jpg', '.jpeg', '.png')

    contador_sucesso = 0

    # 1. Lista os arquivos na pasta local
    arquivos = [f for f in os.listdir(caminho_pasta_fotos) if f.lower().endswith(extensoes)]

    print(f"Processando {len(arquivos)} arquivos...\n")

    for nome_arquivo in arquivos:
        # 2. Extrai a matrícula (Assume que o nome é "Matricula_Nome.jpg")
        # O split('_')[0] pega tudo antes do primeiro underline
        matricula = nome_arquivo.split('_')[0]

        # 3. Define o caminho que o Django salvaria (ex: 'alunos/12345_Joao.jpg')
        # Ajuste o prefixo 'alunos/' conforme o seu upload_to do Django
        caminho_para_db = f"alunos/{nome_arquivo}"

        # 4. Verifica se a matrícula existe na coluna 'matricula_sga'
        cursor.execute("SELECT id FROM core_estudante WHERE matricula_sga = ?", (matricula,))
        registro = cursor.fetchone()

        if registro:
            # 5. Atualiza a coluna 'foto' (VARCHAR)
            try:
                cursor.execute(
                    "UPDATE core_estudante SET foto = ? WHERE matricula_sga = ?",
                    (caminho_para_db, matricula)
                )
                print(f"[OK] Matrícula {matricula}: Vinculada ao arquivo {nome_arquivo}")
                contador_sucesso += 1
            except sqlite3.Error as e:
                print(f"[ERRO] Falha ao atualizar matrícula {matricula}: {e}")
        else:
            print(f"[AVISO] Matrícula {matricula} não encontrada no banco de dados.")

    # Salva e fecha
    conn.commit()
    conn.close()

    print("\n" + "=" * 30)
    print(f"Concluído com sucesso!")
    print(f"Registros atualizados: {contador_sucesso}")
    print("=" * 30)


# --- CONFIGURAÇÃO ---
PASTA_DAS_IMAGENS = r'C:\Caminho\Para\Fotos\Otimizadas'
DB_PATH = 'db.sqlite3'

atualizar_fotos_sqlite(PASTA_DAS_IMAGENS, DB_PATH)