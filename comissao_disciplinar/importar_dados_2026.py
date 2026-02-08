import os
import sys
import django
import pandas as pd
import re
from datetime import datetime

# Configurar o Django ANTES de qualquer importação de modelos
sys.path.append(r'C:\Users\matemarcos\Documents\GitHub\ifb_ocorrencias\comissao_disciplinar')  # AJUSTE ESTE CAMINHO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')

# Inicializar Django
django.setup()
print("✅ Django configurado com sucesso!")

# Importar modelos APÓS o setup do Django
from core.models import Campus, Curso, Turma, Responsavel, Estudante

print("✅ Modelos importados com sucesso!")


def padronizar_telefone(telefone_raw):
    """
    Padroniza números de telefone removendo caracteres especiais e formatando
    Entrada: '(61) 99999-9999' ou '61-999999999' ou '61 99999-9999'
    Saída: '61999999999'
    """
    if pd.isna(telefone_raw) or not telefone_raw:
        return ''

    telefone_raw = str(telefone_raw).strip()

    # Remove todos os caracteres que não são dígitos
    apenas_numeros = re.sub(r'\D', '', telefone_raw)

    # Se tiver 11 dígitos (DDD + 9 dígitos), está OK
    # Se tiver 10 dígitos (DDD + 8 dígitos), também OK
    # Se tiver 9 ou 8 dígitos (sem DDD), assumir DDD 61 (Brasília)
    if len(apenas_numeros) == 9 or len(apenas_numeros) == 8:
        apenas_numeros = '61' + apenas_numeros

    return apenas_numeros


def processar_multiplos_telefones(telefones_raw):
    """
    Processa string com múltiplos telefones separados por vírgula, ponto-e-vírgula ou barra
    Retorna uma lista de telefones padronizados
    """
    if pd.isna(telefones_raw) or not telefones_raw:
        return []

    telefones_raw = str(telefones_raw)

    # Separar por vírgula, ponto-e-vírgula ou barra
    separadores = [',', ';', '/']
    telefones = [telefones_raw]

    for sep in separadores:
        telefones_temp = []
        for tel in telefones:
            telefones_temp.extend(tel.split(sep))
        telefones = telefones_temp

    # Padronizar cada telefone
    telefones_padronizados = [padronizar_telefone(tel) for tel in telefones if tel.strip()]

    # Filtrar telefones vazios ou inválidos (menos de 10 dígitos)
    telefones_validos = [tel for tel in telefones_padronizados if len(tel) >= 10]

    return telefones_validos


def parsear_endereco(endereco_raw):
    """
    Parse do endereço no formato: [logradouro, numero, bairro/cidade, cep, "Municipio"-"UF"]
    Retorna dict com os campos separados
    """
    if pd.isna(endereco_raw) or not endereco_raw:
        return {
            'logradouro': '',
            'numero': '',
            'bairro_cidade': '',
            'cep': '',
            'uf': ''
        }

    endereco_raw = str(endereco_raw).strip()

    try:
        # Remove colchetes externos se existirem
        endereco_raw = endereco_raw.strip('[]')

        # Divide por vírgula
        partes = [p.strip().strip('"').strip("'") for p in endereco_raw.split(',')]

        logradouro = partes[0] if len(partes) > 0 else ''
        numero = partes[1] if len(partes) > 1 else ''
        bairro_cidade = partes[2] if len(partes) > 2 else ''
        cep = partes[3] if len(partes) > 3 else ''

        # Parse da última parte: "Municipio"-"UF"
        municipio_uf = partes[4] if len(partes) > 4 else ''
        uf = ''

        if '-' in municipio_uf:
            uf = municipio_uf.split('-')[-1].strip().strip('"').strip("'")

        # Limpa CEP
        cep = re.sub(r'\D', '', cep)

        return {
            'logradouro': logradouro,
            'numero': numero,
            'bairro_cidade': bairro_cidade,
            'cep': cep,
            'uf': uf.upper()[:2]  # Garante máximo 2 caracteres
        }

    except Exception as e:
        print(f"⚠️  Erro ao parsear endereço '{endereco_raw}': {str(e)}")
        return {
            'logradouro': '',
            'numero': '',
            'bairro_cidade': '',
            'cep': '',
            'uf': ''
        }


def parsear_data(data_raw):
    """
    Tenta parsear data em diversos formatos
    """
    if pd.isna(data_raw) or not data_raw:
        return None

    data_raw = str(data_raw).strip()

    formatos = [
        '%d/%m/%Y',
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%y',
        '%Y/%m/%d'
    ]

    for formato in formatos:
        try:
            return datetime.strptime(data_raw, formato).date()
        except ValueError:
            continue

    print(f"⚠️  Não foi possível parsear a data: {data_raw}")
    return None


def extrair_id_google_drive(link):
    """
    Extrai o ID do arquivo do Google Drive de um link
    Converte para formato: https://drive.google.com/uc?export=view&id=ID
    """
    if pd.isna(link) or not link:
        return ''

    link = str(link).strip()

    # Padrões de URL do Google Drive
    padroes = [
        r'/d/([a-zA-Z0-9_-]+)',  # /d/ID
        r'id=([a-zA-Z0-9_-]+)',  # id=ID
    ]

    for padrao in padroes:
        match = re.search(padrao, link)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=view&id={file_id}"

    # Se não encontrou padrão mas parece ser link do Drive, retorna como está
    if 'drive.google.com' in link:
        return link

    return ''


def criar_turma_2026(nome_turma, campus_padrao):
    """
    Cria turma 2026 automaticamente baseada no nome
    Extrai o código do curso do nome da turma
    Exemplo: TPAV126 -> Curso TPAV
    """
    try:
        # Extrair código do curso do nome da turma
        # Padrão comum: CODIGO + NUMERO + ANO (ex: TPAV126, INFO226)
        # Extrair apenas as letras iniciais como código do curso
        codigo_curso = 'TPAV_Curso'

        if not codigo_curso:
            print(f"⚠️  Não foi possível extrair código do curso de: {nome_turma}")
            return None

        # Buscar curso
        curso = Curso.objects.filter(codigo=codigo_curso).first()

        if not curso:
            print(f"⚠️  Curso não encontrado: {codigo_curso}")
            return None

        # Criar turma 2026
        turma, created = Turma.objects.get_or_create(
            nome=nome_turma,
            curso=curso,
            ano=2026,
            semestre=0,  # Anual
            defaults={
                'periodo': '2026.0',
                'ativa': True
            }
        )

        if created:
            print(f"  + Turma criada: {nome_turma} - {curso.nome} (2026)")

        return turma

    except Exception as e:
        print(f"❌ Erro ao criar turma {nome_turma}: {str(e)}")
        return None


def criar_ou_atualizar_responsavel(nome, email, telefone, endereco_completo, tipo_vinculo):
    """
    Cria ou atualiza um responsável
    Retorna o objeto Responsavel
    """
    if not email or pd.isna(email):
        return None

    email = str(email).strip().lower()
    nome = str(nome).strip() if nome and not pd.isna(nome) else ''

    if not nome or not email:
        return None

    # Validar tipo_vinculo
    tipos_validos = ['PAI', 'MAE', 'TUTOR', 'OUTRO']
    tipo_vinculo = tipo_vinculo.upper() if tipo_vinculo else 'OUTRO'
    if tipo_vinculo not in tipos_validos:
        tipo_vinculo = 'OUTRO'

    # Buscar responsável existente (pode haver duplicatas)
    responsavel = Responsavel.objects.filter(email=email).first()

    if responsavel:
        # Atualizar dados
        responsavel.nome = nome
        responsavel.celular = telefone
        responsavel.endereco = endereco_completo
        responsavel.tipo_vinculo = tipo_vinculo
        responsavel.save()
        print(f"  ↻ Responsável atualizado: {nome}")
    else:
        # Criar novo
        responsavel = Responsavel.objects.create(
            nome=nome,
            email=email,
            celular=telefone,
            endereco=endereco_completo,
            tipo_vinculo=tipo_vinculo,
            preferencia_contato='EMAIL'
        )
        print(f"  + Responsável criado: {nome}")

    return responsavel


def atualizar_estudantes_planilha(arquivo_planilha):
    """
    Atualiza estudantes a partir de uma planilha Excel/CSV
    """
    print(f"\n🎓 ATUALIZANDO ESTUDANTES E RESPONSÁVEIS - 2026")
    print("=" * 70)

    try:
        # Ler planilha
        if arquivo_planilha.endswith('.xlsx') or arquivo_planilha.endswith('.xls'):
            df = pd.read_excel(arquivo_planilha)
        else:
            df = pd.read_csv(arquivo_planilha, encoding='utf-8')

        print(f"📊 Encontradas {len(df)} linhas na planilha\n")

        # Buscar campus padrão
        campus_padrao = Campus.objects.get(sigla='CREM')
        curso_padrao = Curso.objects.get(codigo='TPAV_Curso')

        # Estatísticas
        stats = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0,
            'responsaveis_criados': 0,
            'responsaveis_atualizados': 0
        }

        # Conjunto de matrículas presentes na planilha
        matriculas_planilha = set()

        # Processar cada linha
        for index, row in df.iterrows():
            try:
                # Extrair dados básicos
                matricula_sga = str(row.get('Matrícula', '')).strip()
                nome = str(row.get('Nome', '')).strip()
                cpf = str(row.get('CPF', '')).strip()
                data_nascimento = parsear_data(row.get('Data de Nascimento'))

                # Emails
                email_academico = str(row.get('Email Acadêmico', '')).strip().lower()
                email_google = str(row.get('Email Google Classroom', '')).strip().lower()
                email_pessoal = str(row.get('Email Pessoal', '')).strip().lower()
                email_responsavel = str(row.get('Email do Responsável', '')).strip().lower()

                # Escolher email principal (prioridade: acadêmico > google > pessoal)
                email_principal = email_academico or email_google or email_pessoal

                # Endereço
                endereco_raw = row.get('Endereço', '')
                endereco = parsear_endereco(endereco_raw)

                # Responsáveis
                nome_mae = row.get('Nome da Mãe', '')
                nome_pai = row.get('Nome do Pai', '')
                nome_responsavel = row.get('Responsável', '')

                # Situação
                situacao_curso = str(row.get('Situação no Curso', 'ATIVO')).strip().upper()
                situacao_periodo = str(row.get('Situação no Período', '')).strip()

                # Telefone
                telefone_raw = row.get('Telefone', '')
                telefones = processar_multiplos_telefones(telefone_raw)
                telefone_principal = telefones[0] if telefones else ''

                # Turma e Curso
                nome_turma = str(row.get('Turma', '')).strip()

                # Link da foto
                link_foto = extrair_id_google_drive(row.get('link_foto', ''))

                # Validações básicas
                if not matricula_sga or not nome or not email_principal:
                    print(f"⚠️  Linha {index + 2}: Dados incompletos - pulando")
                    stats['erros'] += 1
                    continue

                matriculas_planilha.add(matricula_sga)

                # Buscar turma (ano 2026)
                turma = None
                curso = None
                if nome_turma:
                    try:
                        # Buscar turma com ano 2026
                        turma = Turma.objects.filter(
                            nome=nome_turma,
                            ano=2026
                        ).first()

                        if turma:
                            curso = turma.curso
                        else:
                            # Criar turma 2026 automaticamente
                            print(f"  ⚙️  Criando turma: {nome_turma} (2026)")
                            turma = criar_turma_2026(nome_turma, campus_padrao)
                            if turma:
                                curso = turma.curso

                    except Exception as e:
                        print(f"⚠️  Erro ao buscar/criar turma {nome_turma}: {str(e)}")

                if not turma or not curso:
                    print(f"⚠️  Linha {index + 2}: Turma/Curso não encontrado - pulando {nome}")
                    stats['erros'] += 1
                    continue

                # Mapear situação
                situacao_map = {
                    'ATIVO': 'ATIVO',
                    'INATIVO': 'INATIVO',
                    'TRANCADO': 'TRANCADO',
                    'EVADIDO': 'EVADIDO',
                    'FORMADO': 'FORMADO',
                    'TRANSFERIDO': 'TRANSFERIDO',
                    'CONCLUÍDO': 'FORMADO',
                    'MATRÍCULA TRANCADA': 'TRANCADO',
                    'CURSANDO': 'ATIVO'
                }
                situacao = situacao_map.get(situacao_curso, 'ATIVO')

                # Criar ou atualizar estudante
                estudante, created = Estudante.objects.get_or_create(
                    matricula_sga=matricula_sga,
                    defaults={
                        'nome': nome,
                        'cpf': cpf,
                        'data_nascimento': data_nascimento,
                        'email': email_principal,
                        'cep': endereco['cep'],
                        'logradouro': endereco['logradouro'],
                        'bairro_cidade': endereco['bairro_cidade'],
                        'uf': endereco['uf'],
                        'turma': turma,
                        'campus': campus_padrao,
                        'curso': curso,
                        'situacao': situacao,
                        'data_ingresso': datetime.now().date(),
                        'foto_url': link_foto
                    }
                )

                if created:
                    print(f"✓ CRIADO: {nome} ({matricula_sga}) - {nome_turma}")
                    stats['criados'] += 1
                else:
                    # Atualizar dados
                    estudante.nome = nome
                    estudante.cpf = cpf
                    if data_nascimento:
                        estudante.data_nascimento = data_nascimento
                    estudante.email = email_principal
                    estudante.cep = endereco['cep']
                    estudante.logradouro = endereco['logradouro']
                    estudante.bairro_cidade = endereco['bairro_cidade']
                    estudante.uf = endereco['uf']
                    estudante.turma = turma
                    estudante.curso = curso
                    estudante.situacao = situacao
                    if link_foto:
                        estudante.foto_url = link_foto
                    estudante.save()

                    print(f"↻ ATUALIZADO: {nome} ({matricula_sga}) - {nome_turma}")
                    stats['atualizados'] += 1

                # Processar responsáveis
                endereco_completo = f"{endereco['logradouro']}, {endereco['numero']}, {endereco['bairro_cidade']}, CEP: {endereco['cep']}, {endereco['uf']}"

                responsaveis_vinculados = []

                # Mãe
                if nome_mae and not pd.isna(nome_mae) and str(nome_mae).strip():
                    resp = criar_ou_atualizar_responsavel(
                        nome_mae,
                        email_responsavel if email_responsavel else f"mae.{matricula_sga}@temp.com",
                        telefone_principal,
                        endereco_completo,
                        'MAE'
                    )
                    if resp:
                        responsaveis_vinculados.append(resp)

                # Pai
                if nome_pai and not pd.isna(nome_pai) and str(nome_pai).strip():
                    resp = criar_ou_atualizar_responsavel(
                        nome_pai,
                        f"pai.{matricula_sga}@temp.com",
                        telefone_principal,
                        endereco_completo,
                        'PAI'
                    )
                    if resp:
                        responsaveis_vinculados.append(resp)

                # Responsável principal (se diferente de mãe/pai)
                if nome_responsavel and not pd.isna(nome_responsavel) and str(nome_responsavel).strip():
                    nome_resp = str(nome_responsavel).strip()
                    if nome_resp != nome_mae and nome_resp != nome_pai:
                        resp = criar_ou_atualizar_responsavel(
                            nome_resp,
                            email_responsavel if email_responsavel else f"resp.{matricula_sga}@temp.com",
                            telefone_principal,
                            endereco_completo,
                            'TUTOR'
                        )
                        if resp:
                            responsaveis_vinculados.append(resp)

                # Vincular responsáveis ao estudante
                if responsaveis_vinculados:
                    estudante.responsaveis.set(responsaveis_vinculados)

            except Exception as e:
                print(f"❌ Erro na linha {index + 2}: {str(e)}")
                import traceback
                traceback.print_exc()
                stats['erros'] += 1
                continue

        # Marcar como inativos estudantes que não estão na planilha
        print(f"\n🔍 Verificando estudantes inativos...")
        estudantes_existentes = Estudante.objects.filter(
            campus=campus_padrao,
            turma__ano=2026
        )

        inativos = 0
        for estudante in estudantes_existentes:
            if estudante.matricula_sga not in matriculas_planilha:
                if estudante.situacao == 'ATIVO':
                    estudante.situacao = 'INATIVO'
                    estudante.save()
                    print(f"  ⊗ Marcado como INATIVO: {estudante.nome} ({estudante.matricula_sga})")
                    inativos += 1

        # Resumo final
        print(f"\n{'=' * 70}")
        print(f"✅ ATUALIZAÇÃO CONCLUÍDA!")
        print(f"📊 RESUMO:")
        print(f"   Estudantes criados: {stats['criados']}")
        print(f"   Estudantes atualizados: {stats['atualizados']}")
        print(f"   Marcados como inativos: {inativos}")
        print(f"   Erros: {stats['erros']}")
        print(f"   Total processado: {len(df)}")
        print(f"{'=' * 70}")

        return stats

    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {arquivo_planilha}")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Função principal"""
    print("🚀 SCRIPT DE ATUALIZAÇÃO DE ESTUDANTES E RESPONSÁVEIS - 2026")
    print("=" * 70)

    # AJUSTE O CAMINHO DO ARQUIVO AQUI
    arquivo_planilha = 'dados_2026.xls'  # ou .csv

    if not os.path.exists(arquivo_planilha):
        print(f"❌ Arquivo não encontrado: {arquivo_planilha}")
        print("Por favor, ajuste o caminho do arquivo na variável 'arquivo_planilha'")
        return

    atualizar_estudantes_planilha(arquivo_planilha)


if __name__ == "__main__":
    main()