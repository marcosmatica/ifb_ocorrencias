import pandas as pd
import os
import django
from datetime import datetime
import sys

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from projetos.models import Projeto, ParticipacaoServidor, ParticipacaoEstudante
from core.models import Servidor, Estudante, Campus


def importar_projetos_da_planilha(caminho_planilha):
    """
    Importa projetos de pesquisa/extensão de uma planilha Excel para o sistema
    """
    try:
        # Ler a planilha
        df = pd.read_excel(caminho_planilha, sheet_name='Controle de processos')
        print(f"Planilha carregada com {len(df)} registros")
        print(f"Colunas: {list(df.columns)}")

        # Mapeamento de situações para as opções do modelo
        mapeamento_situacao = {
            'ENCERRADO': 'FINALIZADO',
            'ENVIADO PARA REGISTRO NA DGRE POR SER RETROATIVO.  RELATÓRIO 2021.2, 2022/1/2 EM ATRASO': 'ATIVO',
            'APENSADO AO PROCESSO Nº  23513.000666.2021-16. ENCERRADO.': 'FINALIZADO',
            'RELATÓRIO 2021/2 ATRASADO': 'ATIVO',
            'RELATÓRIO MAIO-JULHO 2024 ENTREGUE. ENVIADO PARA REGISTRO DE PRORROGAÇÃO': 'ATIVO',
            'PRORROGAÇÃO PARA ABRIL/24 ANEXADA. RELATÓRIO FINAL ANEXADO E REGISTRADO NA PRPI. ENCERRADO.': 'FINALIZADO',
            'RELATÓRIO 2024/1 ENTREGUE. ATA ENTREGUE. REGISTRADO. AGUARDANDO RELATÓRIO 2024/2': 'ATIVO',
            'RELATÓRIO JUL-SET/2024 ENTREGUE. ENVIADO PARA REGISTRO RETROATIVO. REGISTRADO. AGUARDANDO RELATÓRIO OUTUBRO/2024-MARÇO DE 2025.': 'ATIVO',
            'AGUARDANDO PROJETO DE PESQUISA': 'PENDENTE',
            'REGISTRADO. AGUARDO RELATÓRIO 2024/2': 'ATIVO',
            'APENAS RELATÓRIO MAR-AGO/22 ENTREGUE': 'ATIVO',
            'REGISTRADO. ENCAMINHADO A CGEN PARA GUARDA E ACOMPANHAMENTO.': 'ATIVO',
            'REGISTRADO NA PRPI. ENCAMINHADO À CGEN PARA GUARDA E ACOMPANHAMENTO.': 'ATIVO'
        }

        projetos_criados = 0
        erros = []

        for index, row in df.iterrows():
            try:
                print(f"Processando linha {index + 2}...")

                # ========== BUSCAR SERVIDOR COORDENADOR ==========
                nome_servidor = str(row['Servidor']).strip()
                if not nome_servidor or nome_servidor == 'nan':
                    erros.append(f"Servidor vazio na linha {index + 2}")
                    continue

                servidores = Servidor.objects.filter(nome__icontains=nome_servidor)

                if not servidores.exists():
                    servidor = Servidor.objects.filter(nome__icontains='Diego Azevedo Sodre').first()
                else:
                    servidor = servidores.first()
                    if servidores.count() > 1:
                        print(f"Aviso: Múltiplos servidores encontrados para {nome_servidor}. Usando o primeiro.")

                # ========== NÚMERO DO PROCESSO ==========
                numero_processo = str(row['Nº do processo']).strip()
                if not numero_processo or numero_processo == 'nan':
                    erros.append(f"Número do processo vazio na linha {index + 2}")
                    continue

                # Verificar se projeto já existe
                if Projeto.objects.filter(numero_processo=numero_processo).exists():
                    print(f"Projeto {numero_processo} já existe. Pulando...")
                    continue

                # ========== TÍTULO ==========
                titulo = str(row['Título']).strip()
                if not titulo or titulo == 'nan':
                    erros.append(f"Título vazio na linha {index + 2}")
                    continue

                # ========== DATAS ==========
                # Data início
                data_inicio_str = str(row['Início']).strip() if pd.notna(row['Início']) else None
                data_inicio = None

                if data_inicio_str and data_inicio_str != 'nan':
                    try:
                        # Tentar diferentes formatos de data
                        if '/' in data_inicio_str:
                            if len(data_inicio_str.split('/')) == 2:  # Formato "2021 / 1"
                                ano, semestre = data_inicio_str.split('/')
                                ano = ano.strip()
                                semestre = semestre.strip()
                                # Converter para data aproximada
                                mes = 2 if semestre == '1' else 8
                                data_inicio = datetime(int(ano), mes, 1).date()
                            else:  # Formato "1/2020"
                                partes = data_inicio_str.split('/')
                                if len(partes) == 2:
                                    semestre, ano = partes
                                    mes = 2 if semestre.strip() == '1' else 8
                                    data_inicio = datetime(int(ano.strip()), mes, 1).date()
                        else:
                            # Tentar parser automático
                            data_inicio = pd.to_datetime(data_inicio_str).date()
                    except Exception as e:
                        print(f"Erro ao converter data início '{data_inicio_str}': {e}")
                        # Usar data padrão se não conseguir converter
                        data_inicio = datetime(2020, 1, 1).date()
                else:
                    data_inicio = datetime(2020, 1, 1).date()

                # Data final
                data_final_str = str(row['Final']).strip() if pd.notna(row['Final']) else None
                data_final = None

                if data_final_str and data_final_str != 'nan':
                    try:
                        if '/' in data_final_str:
                            if len(data_final_str.split('/')) == 2:  # Formato "2021 / 2"
                                ano, semestre = data_final_str.split('/')
                                ano = ano.strip()
                                semestre = semestre.strip()
                                # Converter para data aproximada
                                mes = 7 if semestre == '1' else 12
                                data_final = datetime(int(ano), mes, 31).date()
                            else:  # Formato "1/2021"
                                partes = data_final_str.split('/')
                                if len(partes) == 2:
                                    semestre, ano = partes
                                    mes = 7 if semestre.strip() == '1' else 12
                                    data_final = datetime(int(ano.strip()), mes, 31).date()
                        else:
                            # Tentar parser automático
                            data_final = pd.to_datetime(data_final_str).date()
                    except Exception as e:
                        print(f"Erro ao converter data final '{data_final_str}': {e}")
                        # Usar data padrão (1 ano após início)
                        data_final = datetime(data_inicio.year + 1, data_inicio.month, data_inicio.day).date()
                else:
                    data_final = datetime(data_inicio.year + 1, data_inicio.month, data_inicio.day).date()

                # ========== TEMA E ÁREA ==========
                tema = str(row['Tema']).strip() if pd.notna(row['Tema']) else 'Não informado'
                area = str(row['Área']).strip() if pd.notna(row['Área']) else 'Não informada'

                # ========== ENVOLVE ESTUDANTES ==========
                envolve_estudantes_str = str(row['Envolve alunos pesquisadores?']).strip().upper() if pd.notna(
                    row['Envolve alunos pesquisadores?']) else 'NÃO'
                envolve_estudantes = envolve_estudantes_str in ['SIM', 'S', 'YES', 'Y', '1', 'VERDADEIRO', 'TRUE']

                # ========== SITUAÇÃO ==========
                situacao_str = str(row['Situação']).strip().upper() if pd.notna(row['Situação']) else 'ATIVO'
                situacao = mapeamento_situacao.get(situacao_str, 'ATIVO')

                # ========== TIPO ==========
                # Como não há informação específica na planilha, assumir pesquisa
                tipo = 'PESQUISA'

                # ========== CRIAR PROJETO ==========
                projeto = Projeto(
                    numero_processo=numero_processo,
                    titulo=titulo,
                    tipo=tipo,
                    data_inicio=data_inicio,
                    data_final=data_final,
                    tema=tema,
                    area=area,
                    coordenador=servidor,
                    envolve_estudantes=envolve_estudantes,
                    situacao=situacao,
                    observacoes=f"Importado da planilha. Situação original: {situacao_str}",
                    periodicidade_relatorio=6,  # Padrão de 6 meses
                    criado_por=servidor
                )

                projeto.save()

                # ========== CRIAR PARTICIPAÇÃO DO COORDENADOR ==========
                # Usar o semestre atual como padrão
                semestre_atual = Projeto.get_semestre_atual()

                # Criar participação com horas_semanais = 0
                participacao = ParticipacaoServidor(
                    projeto=projeto,
                    servidor=servidor,
                    semestre=semestre_atual,
                    horas_semanais=0.5  # Definir como 0 para evitar o erro NOT NULL
                )
                participacao.save()

                projetos_criados += 1
                print(f"✅ Projeto {projetos_criados} criado: {titulo} - {numero_processo}")

            except Exception as e:
                erro_msg = f"Erro na linha {index + 2}: {str(e)}"
                erros.append(erro_msg)
                print(f"❌ {erro_msg}")
                import traceback
                print(traceback.format_exc())
                continue

        # Relatório final
        print("\n" + "=" * 50)
        print("RELATÓRIO DE IMPORTAÇÃO")
        print("=" * 50)
        print(f"✅ Projetos criados com sucesso: {projetos_criados}")
        print(f"❌ Erros encontrados: {len(erros)}")

        if erros:
            print("\nDetalhes dos erros:")
            for erro in erros:
                print(f"  - {erro}")

        return projetos_criados, erros

    except Exception as e:
        print(f"Erro ao processar planilha: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0, [str(e)]


def verificar_pre_importacao(caminho_planilha):
    """
    Verifica a planilha antes da importação
    """
    print("🔍 Verificando planilha...")

    df = pd.read_excel(caminho_planilha, sheet_name='Controle de processos')

    print(f"Total de registros: {len(df)}")
    print(f"Colunas encontradas: {list(df.columns)}")

    # Verificar valores únicos em colunas importantes
    print("\nValores únicos em colunas importantes:")
    print(f"Servidores: {df['Servidor'].unique()}")
    print(f"Situação: {df['Situação'].unique()}")

    # Verificar dados faltantes
    print("\nDados faltantes:")
    for coluna in df.columns:
        faltantes = df[coluna].isna().sum()
        if faltantes > 0:
            print(f"  {coluna}: {faltantes} valores faltantes")

    # Mostrar alguns exemplos de datas para debug
    print("\nExemplos de datas (Início):")
    for i, data in enumerate(df['Início'].head()):
        print(f"  {i + 1}: {data} (tipo: {type(data)})")

    print("\nExemplos de datas (Final):")
    for i, data in enumerate(df['Final'].head()):
        print(f"  {i + 1}: {data} (tipo: {type(data)})")


# USO DO SCRIPT
if __name__ == "__main__":
    # Caminho para a planilha - AJUSTE ESTE CAMINHO
    caminho_planilha = r"C:\Users\marco\OneDrive\Área de Trabalho\Planilha de Projetos de Pesquisa Registrados.xlsx"

    # Verificar antes de importar
    verificar_pre_importacao(caminho_planilha)

    # Confirmar importação
    resposta = input("\nDeseja prosseguir com a importação? (s/n): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print("\n🚀 Iniciando importação...")
        sucesso, erros = importar_projetos_da_planilha(caminho_planilha)

        if sucesso > 0:
            print(f"\n🎉 Importação concluída! {sucesso} projetos importados.")
        else:
            print("\n❌ Nenhum projeto foi importado devido a erros.")
    else:
        print("Importação cancelada.")