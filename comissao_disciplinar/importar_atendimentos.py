import pandas as pd
import os
import django
from datetime import datetime
import sys

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from atendimentos.models import Atendimento, TipoAtendimento, SituacaoAtendimento
from core.models import Estudante, Servidor


def importar_atendimentos_da_planilha(caminho_planilha):
    """
    Importa atendimentos de uma planilha Excel para o sistema
    """
    try:
        # Ler a planilha
        df = pd.read_excel(caminho_planilha)
        print(f"Planilha carregada com {len(df)} registros")

        # Mapeamento de origens para as opções do modelo
        mapeamento_origem = {
            'ESPONTÂNEO': 'ESPONTANEO',
            'ESPONTANEA': 'ESPONTANEO',
            'ESPONTÂNEA': 'ESPONTANEO',
            'ENCAMINHAMENTO': 'ENCAMINHAMENTO',
            'SOLICITAÇÃO DOCENTE': 'SOLICITACAO_DOCENTE',
            'SOLICITAÇÃO DE DOCENTE': 'SOLICITACAO_DOCENTE',
            'SOLICITAÇÃO COORDENAÇÃO': 'SOLICITACAO_COORDENACAO',
            'SOLICITAÇÃO DE COORDENAÇÃO': 'SOLICITACAO_COORDENACAO',
            'OUTRO': 'OUTRO',
            'OUTROS': 'OUTRO'
        }

        # Mapeamento de coordenações/setores
        mapeamento_coordenacao = {
            'CDPD': 'CDPD',
            'CDAE': 'CDAE',
            'NAPNE': 'NAPNE',
            'PEDAGÓGICA': 'CPED',
            'COORDENAÇÃO PEDAGÓGICA': 'CPED',
            'COORDENAÇÃO DE CURSO': 'CC',
            'COORDENAÇÃO GERAL': 'CGEN',
            'DIRETORIA DE ENSINO': 'DREP',
            'DIRETORIA GERAL': 'DG',
            'PSICOLOGIA': 'PSIC',
            'ASSISTÊNCIA SOCIAL': 'ASOC'
        }

        atendimentos_criados = 0
        erros = []

        for index, row in df.iterrows():
            try:
                print(f"Processando linha {index + 2}...")

                # ========== BUSCAR ESTUDANTE ==========
                nome_estudante = str(row['ALUNO']).replace('  ', ' ').strip()
                turma_estudante = str(row['TURMA']).strip() if pd.notna(row['TURMA']) else None

                # Buscar estudante por nome e turma
                estudantes = Estudante.objects.filter(nome__icontains=nome_estudante)
                if turma_estudante:
                    estudantes = estudantes.filter(turma__nome__icontains=turma_estudante)

                if not estudantes.exists():
                    erros.append(f"Estudante não encontrado: {nome_estudante} - Turma: {turma_estudante}")
                    continue

                estudante = estudantes.first()
                if estudantes.count() > 1:
                    print(f"Aviso: Múltiplos estudantes encontrados para {nome_estudante}. Usando o primeiro.")

                # ========== BUSCAR SERVIDOR RESPONSÁVEL ==========
                nome_servidor = str(row['PROFISSIONAL RESPONSÁVEL PELO ATENDIMENTO']).strip()
                servidores = Servidor.objects.filter(nome__icontains=nome_servidor)

                if not servidores.exists():
                    # Tentar criar um servidor temporário se não existir
                    servidor, created = Servidor.objects.get_or_create(
                        nome=nome_servidor,
                        defaults={
                            'email': f"{nome_servidor.lower().replace(' ', '.')}@ifb.edu.br",
                            'coordenacao': 'CDAE',
                            'ativo': True
                        }
                    )
                    if created:
                        print(f"Servidor criado: {servidor.nome}")
                else:
                    servidor = servidores.first()

                # ========== TIPO DE ATENDIMENTO ==========
                nome_tipo = str(row['TIPO DE ATENDIMENTO']).strip()
                tipo_atendimento, created = TipoAtendimento.objects.get_or_create(
                    nome=nome_tipo,
                    defaults={'descricao': f'Tipo de atendimento: {nome_tipo}', 'ativo': True}
                )

                # ========== SITUAÇÃO DO ATENDIMENTO ==========
                nome_situacao = str(row['SITUAÇÃO DO ATENDIMENTO']).strip()
                situacao_atendimento, created = SituacaoAtendimento.objects.get_or_create(
                    nome=nome_situacao,
                    defaults={'ativo': True}
                )

                # ========== ORIGEM ==========
                origem_str = str(row['ORIGEM DO ATENDIMENTO']).strip().upper()
                origem = mapeamento_origem.get(origem_str, 'OUTRO')

                # ========== COORDENAÇÃO/SETOR ==========
                setor_str = str(row['SETOR']).strip().upper() if pd.notna(row['SETOR']) else 'OUTRO'
                coordenacao = mapeamento_coordenacao.get(setor_str, 'OUTRO')

                # ========== DATAS ==========
                # Data do atendimento
                data_atendimento = row['DATA DO ATENDIMENTO']
                print(data_atendimento)
                if pd.isna(data_atendimento):
                    erros.append(f"Data do atendimento vazia para {nome_estudante}")
                    continue

                # Converter para datetime se for string
                if isinstance(data_atendimento, str):
                    try:
                        data_atendimento = datetime.strptime(data_atendimento, '%d/%m/%Y %h:%m:%s').date()
                    except:
                        data_atendimento = datetime.strptime(data_atendimento, '%Y-%m-%d %h:%m:%s').date()
                else:
                    # Se for objeto datetime do pandas
                    data_atendimento = data_atendimento.date()

                # Data e hora (finalização/encaminhamento)
                #data_hora_str = row['DATA E HORA']
                hora_atendimento = None

                #if pd.notna(data_hora_str):
                #    if isinstance(data_hora_str, str):
                #        try:
                            # Tentar extrair hora de string datetime
                #            dt = datetime.strptime(data_hora_str, '%d/%m/%Y %H:%M')
                #            hora_atendimento = dt.time()
                #        except:
                #            try:
                                # Tentar apenas hora
                #                hora_atendimento = datetime.strptime(data_hora_str, '%H:%M').time()
                #            except:
                #                hora_atendimento = None
                #    else:
                        # Se for objeto datetime
                #        hora_atendimento = data_hora_str.time()

                # Se não conseguiu extrair hora, usar hora padrão
                if not hora_atendimento:
                    hora_atendimento = datetime.strptime('08:00', '%H:%M').time()

                # ========== INFORMAÇÕES ==========
                informacoes = str(
                    row['INFORMAÇÕES PARA FICHA DO ALUNO OU ENCAMINHAMENTO A OUTROS SETORES']) if pd.notna(row[
                                                                                                                'INFORMAÇÕES PARA FICHA DO ALUNO OU ENCAMINHAMENTO A OUTROS SETORES']) else f"Atendimento de {nome_tipo} realizado em {data_atendimento.strftime('%d/%m/%Y')}"

                # ========== PUBLICAR NA FICHA ==========
                publicar_ficha_str = str(row['Ficha do estudante?']).strip().upper() if pd.notna(
                    row['Ficha do estudante?']) else 'NÃO'
                publicar_ficha = publicar_ficha_str in ['SIM', 'S', 'YES', 'Y', '1', 'VERDADEIRO', 'TRUE', 'verdadeiro']

                # ========== CRIAR ATENDIMENTO ==========
                atendimento = Atendimento(
                    coordenacao=coordenacao,
                    servidor_responsavel=servidor,
                    data=data_atendimento,
                    hora=hora_atendimento,
                    tipo_atendimento=tipo_atendimento,
                    situacao=situacao_atendimento,
                    origem=origem,
                    informacoes=informacoes,
                    publicar_ficha_aluno=publicar_ficha,
                )

                atendimento.save()

                # Adicionar estudante ao atendimento
                atendimento.estudantes.add(estudante)

                # Adicionar servidor responsável como participante também
                atendimento.servidores_participantes.add(servidor)

                atendimentos_criados += 1
                print(f"✅ Atendimento {atendimentos_criados} criado: {estudante.nome} - {data_atendimento}")

            except Exception as e:
                erro_msg = f"Erro na linha {index + 2}: {str(e)}"
                erros.append(erro_msg)
                print(f"❌ {erro_msg}")
                continue

        # Relatório final
        print("\n" + "=" * 50)
        print("RELATÓRIO DE IMPORTAÇÃO")
        print("=" * 50)
        print(f"✅ Atendimentos criados com sucesso: {atendimentos_criados}")
        print(f"❌ Erros encontrados: {len(erros)}")

        if erros:
            print("\nDetalhes dos erros:")
            for erro in erros:
                print(f"  - {erro}")

        return atendimentos_criados, erros

    except Exception as e:
        print(f"Erro ao processar planilha: {str(e)}")
        return 0, [str(e)]


def verificar_pre_importacao(caminho_planilha):
    """
    Verifica a planilha antes da importação
    """
    print("🔍 Verificando planilha...")

    df = pd.read_excel(caminho_planilha)

    print(f"Total de registros: {len(df)}")
    print(f"Colunas encontradas: {list(df.columns)}")

    # Verificar valores únicos em colunas importantes
    print("\nValores únicos em colunas importantes:")
    print(f"Tipo de Atendimento: {df['TIPO DE ATENDIMENTO'].unique()}")
    print(f"Situação: {df['SITUAÇÃO DO ATENDIMENTO'].unique()}")
    print(f"Origem: {df['ORIGEM DO ATENDIMENTO'].unique()}")
    print(f"Setor: {df['SETOR'].unique()}")

    # Verificar dados faltantes
    print("\nDados faltantes:")
    for coluna in df.columns:
        faltantes = df[coluna].isna().sum()
        if faltantes > 0:
            print(f"  {coluna}: {faltantes} valores faltantes")


# USO DO SCRIPT
if __name__ == "__main__":
    # Caminho para a planilha - AJUSTE ESTE CAMINHO
    caminho_planilha = r"C:\Users\marco\OneDrive\Área de Trabalho\importar_atendimentos.xlsx"

    # Verificar antes de importar
    verificar_pre_importacao(caminho_planilha)

    # Confirmar importação
    resposta = input("\nDeseja prosseguir com a importação? (s/n): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print("\n🚀 Iniciando importação...")
        sucesso, erros = importar_atendimentos_da_planilha(caminho_planilha)

        if sucesso > 0:
            print(f"\n🎉 Importação concluída! {sucesso} atendimentos importados.")
        else:
            print("\n❌ Nenhum atendimento foi importado devido a erros.")
    else:
        print("Importação cancelada.")