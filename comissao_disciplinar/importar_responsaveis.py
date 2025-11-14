import csv
import os
import django
import requests
import time
from datetime import datetime

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')
django.setup()

from core.models import Estudante, Responsavel, Turma, Curso, Campus
from django.db import transaction
ceps = []

def buscar_cep(cep):
    """
    Busca endereço completo usando a API ViaCEP
    Retorna: { 'logradouro', 'bairro', 'localidade', 'uf', 'erro' }
    """
    cep_limpo = ''.join(filter(str.isdigit, cep))
    if cep_limpo not in ceps:
        ceps.append(cep_limpo)
    else:
        return {'erro': 'CEP já buscado'}

    if len(cep_limpo) != 8:
        return {'erro': 'CEP inválido'}

    try:
        url = f'https://viacep.com.br/ws/{cep_limpo}/json/'
        response = requests.get(url, timeout=0.1)

        if response.status_code == 200:
            data = response.json()

            if 'erro' not in data:
                return {
                    'logradouro': data.get('logradouro', ''),
                    'bairro': data.get('bairro', ''),
                    'cidade': data.get('localidade', ''),
                    'uf': data.get('uf', ''),
                    'cep': data.get('cep', cep_limpo)
                }
            else:
                return {'erro': 'CEP não encontrado'}
        else:
            return {'erro': f'Erro na API: {response.status_code}'}

    except requests.exceptions.RequestException as e:
        return {'erro': f'Erro de conexão: {str(e)}'}
    except Exception as e:
        return {'erro': f'Erro inesperado: {str(e)}'}


def formatar_endereco(dados_cep):
    """Formata os dados do CEP em um endereço completo"""
    if 'erro' in dados_cep:
        return f"CEP: {dados_cep.get('cep', '')} - {dados_cep['erro']}"

    partes = []
    if dados_cep.get('logradouro'):
        partes.append(dados_cep['logradouro'])
    if dados_cep.get('bairro'):
        partes.append(dados_cep['bairro'])
    if dados_cep.get('cidade'):
        partes.append(dados_cep['cidade'])
    if dados_cep.get('uf'):
        partes.append(dados_cep['uf'])
    if dados_cep.get('cep'):
        partes.append(f"CEP: {dados_cep['cep']}")

    return ', '.join(partes) if partes else 'Endereço não encontrado'


def parse_contatos(contatos_str):
    """Extrai números de telefone da string de contatos"""
    if not contatos_str:
        return []

    # Remove espaços e divide por vírgulas ou espaços
    numbers = []
    for part in contatos_str.replace(',', ' ').split():
        # Mantém apenas dígitos
        clean_number = ''.join(filter(str.isdigit, part))
        if len(clean_number) >= 8:  # Número válido
            numbers.append(clean_number)

    return numbers


def get_or_create_responsavel(nome, email, celular, cep, tipo_vinculo):
    """Obtém ou cria um responsável, evitando duplicatas"""
    if not nome or nome.strip() == '':
        return None

    # Limpa e padroniza o nome
    nome = nome.strip().title()

    # Busca CEP se fornecido
    endereco_completo = ""
    if cep:
        print(f"Buscando CEP: {cep}")
        dados_cep = buscar_cep(cep)
        endereco_completo = formatar_endereco(dados_cep)

        # Pequena pausa para não sobrecarregar a API
        time.sleep(0.5)
    else:
        endereco_completo = "Endereço não informado"

    # Verifica se já existe um responsável com mesmo nome e tipo de vínculo
    try:
        responsavel = Responsavel.objects.filter(
            nome=nome,
            #tipo_vinculo=tipo_vinculo
        ).first()

        if responsavel:
            # Atualiza informações se necessário
            atualizado = False
            if email and not responsavel.email:
                responsavel.email = email
                atualizado = True
            if celular and not responsavel.celular:
                responsavel.celular = celular
                atualizado = True
            if cep and not responsavel.endereco.startswith('CEP:'):
                responsavel.endereco = endereco_completo
                atualizado = True

            if atualizado:
                responsavel.save()
                print(f"Atualizado responsável: {nome}")

            return responsavel
    except Responsavel.DoesNotExist:
        pass

    # Cria novo responsável
    responsavel = Responsavel.objects.create(
        nome=nome,
        email=email or '',
        celular=celular or '',
        endereco=endereco_completo,
        tipo_vinculo=tipo_vinculo,
        preferencia_contato='CELULAR' if celular else 'EMAIL'
    )

    print(f"Criado novo responsável: {nome} - {endereco_completo}")
    return responsavel


def importar_dados_csv(caminho_arquivo):
    """Importa dados do CSV e cria relacionamentos"""

    stats = {
        'total_linhas': 0,
        'estudantes_processados': 0,
        'responsaveis_criados': 0,
        'responsaveis_vinculados': 0,
        'erros': 0
    }

    with open(caminho_arquivo, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pular cabeçalho

        with transaction.atomic():
            for linha in reader:
                stats['total_linhas'] += 1

                if len(linha) < 8:
                    print(f"Linha {stats['total_linhas']} incompleta: {linha}")
                    stats['erros'] += 1
                    continue

                try:
                    # Extrair dados da linha
                    turma_nome = linha[0].strip()
                    matricula = linha[1].strip()
                    nome_pai = linha[2].strip() if len(linha) > 2 and linha[2].strip() else None
                    nome_mae = linha[3].strip() if len(linha) > 3 and linha[3].strip() else None
                    email_1 = linha[4].strip() if len(linha) > 4 and linha[4].strip() else None
                    email_2 = linha[5].strip() if len(linha) > 5 and linha[5].strip() else None
                    cep = linha[6].strip() if len(linha) > 6 and linha[6].strip() else None
                    contatos_str = linha[7].strip() if len(linha) > 7 and linha[7].strip() else None

                    # Buscar estudante pela matrícula
                    try:
                        estudante = Estudante.objects.get(matricula_sga=matricula)
                        stats['estudantes_processados'] += 1
                    except Estudante.DoesNotExist:
                        print(f"Estudante com matrícula {matricula} não encontrado. Pulando...")
                        stats['erros'] += 1
                        continue

                    # Processar contatos
                    numeros_contato = parse_contatos(contatos_str)
                    celular_pai = numeros_contato[0] if numeros_contato else None
                    celular_mae = numeros_contato[1] if len(numeros_contato) > 1 else celular_pai

                    # Criar/obter responsáveis
                    responsaveis = []

                    # Pai
                    if nome_pai:
                        responsavel_pai = get_or_create_responsavel(
                            nome=nome_pai,
                            email=email_1,
                            celular=celular_pai,
                            cep=cep,
                            tipo_vinculo='PAI'
                        )
                        if responsavel_pai:
                            responsaveis.append(responsavel_pai)
                            stats['responsaveis_criados'] += 1

                    # Mãe
                    if nome_mae:
                        responsavel_mae = get_or_create_responsavel(
                            nome=nome_mae,
                            email=email_2 or email_1,  # Usa email_1 se email_2 não existir
                            celular=celular_mae,
                            cep=cep,
                            tipo_vinculo='MAE'
                        )
                        if responsavel_mae:
                            responsaveis.append(responsavel_mae)
                            stats['responsaveis_criados'] += 1

                    # Adicionar responsáveis ao estudante (relacionamento N para N)
                    if responsaveis:
                        estudante.responsaveis.add(*responsaveis)
                        stats['responsaveis_vinculados'] += len(responsaveis)
                        print(f"Adicionados {len(responsaveis)} responsáveis ao estudante {estudante.nome}")

                    # Mostrar progresso a cada 10 linhas
                    if stats['total_linhas'] % 10 == 0:
                        print(f"Processadas {stats['total_linhas']} linhas...")

                except Exception as e:
                    print(f"Erro ao processar linha {stats['total_linhas']}: {linha}")
                    print(f"Erro: {str(e)}")
                    stats['erros'] += 1
                    continue

    return stats


# ALTERAÇÕES NECESSÁRIAS NOS MODELOS:

# 1. No models.py, altere o campo responsavel em Estudante para ManyToManyField:
"""
class Estudante(models.Model):
    # ... outros campos ...

    # ALTERAR DE:
    # responsavel = models.ForeignKey(
    #     Responsavel,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )

    # PARA:
    responsaveis = models.ManyToManyField(
        Responsavel,
        related_name='estudantes',
        blank=True
    )
"""

# 2. Execute as migrações:
"""
python manage.py makemigrations core
python manage.py migrate core
"""

if __name__ == '__main__':
    caminho_csv = 'importar_responsaveis.csv'  # Ajuste o caminho se necessário

    print("Iniciando importação de responsáveis com busca de CEP...")
    print("=" * 50)

    stats = importar_dados_csv(caminho_csv)

    print("\n" + "=" * 50)
    print("IMPORTAÇÃO CONCLUÍDA!")
    print(f"Total de linhas processadas: {stats['total_linhas']}")
    print(f"Estudantes processados: {stats['estudantes_processados']}")
    print(f"Responsáveis criados/atualizados: {stats['responsaveis_criados']}")
    print(f"Vínculos criados: {stats['responsaveis_vinculados']}")
    print(f"Erros: {stats['erros']}")