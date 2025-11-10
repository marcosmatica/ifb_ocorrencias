import os
import django
import csv
from datetime import datetime
from django.db import transaction

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from atendimentos.models import Atendimento, TipoAtendimento, SituacaoAtendimento
from core.models import Estudante, Servidor, Coordenacao


def importar_saidas_antecipadas(caminho_arquivo):
    """
    Importa atendimentos de saída antecipada do arquivo CSV
    """

    # Obter ou criar tipo de atendimento para Saída Antecipada
    tipo_atendimento, created = TipoAtendimento.objects.get_or_create(
        nome='Saída Antecipada',
        defaults={'descricao': 'Registro de saída antecipada do aluno', 'ativo': True}
    )

    # Obter ou criar situação para Concluído
    situacao, created = SituacaoAtendimento.objects.get_or_create(
        nome='Concluído',
        defaults={'cor': '#28a745', 'ativo': True}
    )

    with open(caminho_arquivo, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pular cabeçalho

        atendimentos_importados = 0
        erros = []

        for linha_num, linha in enumerate(reader, start=2):
            try:
                # Pular linhas vazias
                if not linha or len(linha) < 8 or not linha[2].strip():
                    continue

                # Extrair dados da linha
                nome_estudante = linha[2].strip()
                turma_estudante = linha[3].strip() if len(linha) > 3 else ''
                data_hora_str = linha[4].strip() if len(linha) > 4 else ''
                origem_str = linha[5].strip() if len(linha) > 5 else ''
                servidor_str = linha[6].strip() if len(linha) > 6 else ''
                observacoes = linha[7].strip() if len(linha) > 7 else ''

                # Processar data e hora
                if data_hora_str:
                    try:
                        data_hora = datetime.strptime(data_hora_str, '%d/%m/%Y %H:%M:%S')
                        data = data_hora.date()
                        hora = data_hora.time()
                    except ValueError:
                        print(f"Erro na linha {linha_num}: Formato de data inválido - {data_hora_str}")
                        continue
                else:
                    continue

                # Buscar estudante
                estudantes = Estudante.objects.filter(nome__icontains=nome_estudante)
                if not estudantes.exists():
                    print(f"Estudante não encontrado na linha {linha_num}: {nome_estudante}")
                    erros.append(f"Linha {linha_num}: Estudante '{nome_estudante}' não encontrado")
                    continue

                estudante = estudantes.first()
                if estudantes.count() > 1:
                    print(f"⚠️  Múltiplos estudantes encontrados para '{nome_estudante}'. Usando o primeiro.")

                # Buscar servidor responsável
                # Extrair nome do servidor (remover cargo entre parênteses)
                nome_servidor = servidor_str.split('(')[0].strip() if '(' in servidor_str else servidor_str
                servidores = Servidor.objects.filter(nome__icontains=nome_servidor)

                if not servidores.exists():
                    print(f"Servidor não encontrado na linha {linha_num}: {nome_servidor}")
                    erros.append(f"Linha {linha_num}: Servidor '{nome_servidor}' não encontrado")
                    continue

                servidor_responsavel = servidores.first()
                if servidores.count() > 1:
                    print(f"⚠️  Múltiplos servidores encontrados para '{nome_servidor}'. Usando o primeiro.")

                # Mapear origem
                origem_map = {
                    'Presencial (responsável)': 'PRESENCIAL',
                    'Presencial (próprio aluno)': 'PRESENCIAL',
                    'Presencial (aluno maior de idade)': 'PRESENCIAL',
                    'Contato telefônico': 'CONTATO_TELEFONICO',
                    'Whatsapp': 'CONTATO_WHATSAPP',
                    'Encaminhamento': 'ENCAMINHAMENTO'
                }

                origem = origem_map.get(origem_str, 'OUTRO')

                # Determinar coordenação (CDAE)
                coordenacao = 'CDAE'

                # Criar informações do atendimento
                informacoes = f"""Saída antecipada do estudante {nome_estudante}
Turma: {turma_estudante}
Origem: {origem_str}
Observações: {observacoes}
Importado automaticamente do sistema anterior"""

                # Criar atendimento
                with transaction.atomic():
                    atendimento = Atendimento(
                        coordenacao=coordenacao,
                        data=data,
                        hora=hora,
                        tipo_atendimento=tipo_atendimento,
                        situacao=situacao,
                        origem=origem,
                        informacoes=informacoes,
                        observacoes=observacoes,
                        servidor_responsavel=servidor_responsavel,
                        publicar_ficha_aluno=True
                    )
                    atendimento.save()

                    # Adicionar estudante ao atendimento
                    atendimento.estudantes.add(estudante)

                    atendimentos_importados += 1
                    print(f"✅ Atendimento importado: {nome_estudante} - {data}")

            except Exception as e:
                erro_msg = f"Erro na linha {linha_num}: {str(e)}"
                print(erro_msg)
                erros.append(erro_msg)
                continue

    # Relatório final
    print(f"\n{'=' * 50}")
    print("RELATÓRIO DE IMPORTAÇÃO")
    print(f"{'=' * 50}")
    print(f"✅ Atendimentos importados com sucesso: {atendimentos_importados}")
    print(f"❌ Erros encontrados: {len(erros)}")

    if erros:
        print(f"\nErros detalhados:")
        for erro in erros:
            print(f"  - {erro}")


if __name__ == '__main__':
    caminho_csv = r'C:\Users\marco\OneDrive\Área de Trabalho\importar_atendimentos.csv'  # Ajuste o caminho se necessário

    if not os.path.exists(caminho_csv):
        print(f"❌ Arquivo não encontrado: {caminho_csv}")
    else:
        print("Iniciando importação de saídas antecipadas...")
        importar_saidas_antecipadas(caminho_csv)