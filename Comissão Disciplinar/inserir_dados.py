import os
import sys
import django
import pandas as pd
from datetime import datetime

# Configurar o Django ANTES de qualquer importação de modelos
sys.path.append(r'C:\Users\marco\OneDrive\Documentos\GitHub\Selenium_IFB\Comissão Disciplinar')  # AJUSTE ESTE CAMINHO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')

# Inicializar Django
django.setup()
print("✅ Django configurado com sucesso!")

# Importar modelos APÓS o setup do Django
from django.contrib.auth.models import User
from core.models import Campus, Curso, Turma, Responsavel, Estudante, Servidor, Infracao, Sancao

print("✅ Modelos importados com sucesso!")


def criar_campus_padrao():
    """Cria o campus Recanto das Emas se não existir"""
    campus, created = Campus.objects.get_or_create(
        sigla='CREM',
        defaults={
            'nome': 'Recanto das Emas',
            'ativo': True
        }
    )
    if created:
        print(f"✅ Campus criado: {campus.nome}")
    else:
        print(f"ℹ️  Campus já existe: {campus.nome}")
    return campus


def criar_cursos_padrao(campus):
    """Cria cursos padrão do IFB"""
    cursos_data = [
        {'codigo': 'TPAV', 'nome': 'Técnico em Produção Audiovisual'},
    ]

    cursos_criados = 0
    for curso_data in cursos_data:
        curso, created = Curso.objects.get_or_create(
            codigo=curso_data['codigo'],
            defaults={
                'nome': curso_data['nome'],
                'campus': campus,
                'ativo': True
            }
        )
        if created:
            cursos_criados += 1
            print(f"✅ Curso criado: {curso.nome}")
        else:
            print(f"ℹ️  Curso já existe: {curso.nome}")

    return cursos_criados


def criar_turmas_padrao():
    """Cria turmas padrão para o ano atual"""
    ano_atual = datetime.now().year
    semestre = 0

    turmas_data = []
    cursos = Curso.objects.all()

    for curso in cursos:
        # Cria algumas turmas para cada curso
        for i in range(1, 4):  # 3 turmas por curso
            nome_turma = f"{curso.codigo}{i}{ano_atual % 100}"
            turmas_data.append({
                'nome': nome_turma,
                'curso': curso,
                'ano': ano_atual,
                'semestre': semestre,
                'ativa': True
            })

    turmas_criadas = 0
    for turma_data in turmas_data:
        turma, created = Turma.objects.get_or_create(
            nome=turma_data['nome'],
            curso=turma_data['curso'],
            ano=turma_data['ano'],
            semestre=turma_data['semestre'],
            defaults=turma_data
        )
        if created:
            turmas_criadas += 1
            print(f"✅ Turma criada: {turma.nome}")
        else:
            print(f"ℹ️  Turma já existe: {turma.nome}")

    return turmas_criadas


def importar_responsaveis(arquivo_csv):
    """Importa responsáveis de um arquivo CSV"""
    print(f"\n👨‍👩‍👧‍👦 IMPORTANDO RESPONSÁVEIS de {arquivo_csv}")
    print("=" * 50)

    try:
        df = pd.read_csv(arquivo_csv, encoding='utf-8')
        print(f"Encontradas {len(df)} linhas no arquivo")

        responsaveis_criados = 0
        responsaveis_duplicados = 0

        for index, row in df.iterrows():
            try:
                # Limpar e formatar os dados
                email = str(row.get('email', '')).strip().lower()
                nome = str(row.get('nome', '')).strip()
                celular = str(row.get('celular', '')).strip()
                endereco = str(row.get('endereco', '')).strip()
                tipo_vinculo = str(row.get('tipo_vinculo', '')).strip().upper()
                preferencia_contato = str(row.get('preferencia_contato', 'EMAIL')).strip().upper()

                if not email:
                    print(f"⚠️  Linha {index + 2}: Email vazio - pulando")
                    continue

                # Verificar se já existe
                if Responsavel.objects.filter(email=email).exists():
                    print(f"→ Já existe: {nome} ({email})")
                    responsaveis_duplicados += 1
                    continue

                # Validar tipo_vinculo
                tipos_validos = ['PAI', 'MAE', 'TUTOR', 'OUTRO']
                if tipo_vinculo not in tipos_validos:
                    tipo_vinculo = 'OUTRO'

                # Validar preferencia_contato
                preferencias_validas = ['EMAIL', 'CELULAR', 'WHATSAPP']
                if preferencia_contato not in preferencias_validas:
                    preferencia_contato = 'EMAIL'

                # Criar responsável
                responsavel = Responsavel(
                    nome=nome,
                    email=email,
                    celular=celular,
                    endereco=endereco,
                    tipo_vinculo=tipo_vinculo,
                    preferencia_contato=preferencia_contato
                )
                responsavel.save()

                responsaveis_criados += 1
                print(f"✓ Criado: {nome} ({email}) - {tipo_vinculo}")

            except Exception as e:
                print(f"❌ Erro na linha {index + 2}: {str(e)}")
                continue

        print(f"\n✅ RESUMO RESPONSÁVEIS:")
        print(f"   Total processados: {len(df)}")
        print(f"   Novos responsáveis: {responsaveis_criados}")
        print(f"   Duplicados: {responsaveis_duplicados}")
        print(f"   Erros: {len(df) - responsaveis_criados - responsaveis_duplicados}")

        return responsaveis_criados

    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {arquivo_csv}")
        return 0
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def importar_estudantes(arquivo_csv):
    """Importa estudantes de um arquivo CSV"""
    print(f"\n🎓 IMPORTANDO ESTUDANTES de {arquivo_csv}")
    print("=" * 50)

    try:
        df = pd.read_csv(arquivo_csv, encoding='utf-8')
        print(f"Encontradas {len(df)} linhas no arquivo")

        estudantes_criados = 0
        estudantes_duplicados = 0

        campus_padrao = Campus.objects.get(sigla='CREM')

        for index, row in df.iterrows():
            try:
                # Limpar e formatar os dados
                matricula_sga = str(row.get('matricula_sga', '')).strip()
                nome = str(row.get('nome', '')).strip()
                email = str(row.get('email', '')).strip().lower()
                codigo_curso = str(row.get('curso', '')).strip()
                nome_turma = str(row.get('turma', '')).strip()
                email_responsavel = str(row.get('responsavel', '')).strip().lower()
                situacao = str(row.get('situacao', 'ATIVO')).strip().upper()
                data_ingresso = datetime.now().date()

                if not matricula_sga:
                    print(f"⚠️  Linha {index + 2}: Matrícula SGA vazia - pulando")
                    continue

                # Verificar se já existe
                if Estudante.objects.filter(matricula_sga=matricula_sga).exists():
                    print(f"→ Já existe: {nome} ({matricula_sga})")
                    estudantes_duplicados += 1
                    continue

                # Buscar curso
                try:
                    cursos = Curso.objects.all()
                    print(cursos)
                    curso = Curso.objects.get(codigo=codigo_curso, campus=campus_padrao)
                except Curso.DoesNotExist:
                    print(f"❌ Curso não encontrado: {codigo_curso} - pulando estudante {nome}")
                    continue

                # Buscar turma
                try:

                    turma = Turma.objects.get(nome=nome_turma, curso=curso)
                except Turma.DoesNotExist:
                    print(f"❌ Turma não encontrada: {nome_turma} - pulando estudante {nome}")
                    continue

                # Buscar responsável (opcional)
                responsavel = None
                if email_responsavel:
                    try:
                        responsavel = Responsavel.objects.get(email=email_responsavel)
                    except Responsavel.DoesNotExist:
                        print(f"⚠️  Responsável não encontrado: {email_responsavel} - estudante será criado sem responsável")

                # Validar situação
                situacoes_validas = ['ATIVO', 'TRANCADO', 'EVADIDO', 'FORMADO', 'TRANSFERIDO']
                if situacao not in situacoes_validas:
                    situacao = 'ATIVO'

                # Converter data_ingresso se for string
                if isinstance(data_ingresso, str):
                    try:
                        data_ingresso = datetime.strptime(data_ingresso, '%Y-%m-%d').date()
                    except:
                        data_ingresso = datetime.now().date()

                # Criar estudante
                estudante = Estudante(
                    matricula_sga=matricula_sga,
                    nome=nome,
                    email=email,
                    turma=turma,
                    campus=campus_padrao,
                    curso=curso,
                    responsavel=responsavel,
                    situacao=situacao,
                    data_ingresso=data_ingresso
                )
                estudante.save()

                estudantes_criados += 1
                print(f"✓ Criado: {nome} ({matricula_sga}) - {curso.codigo}/{turma.nome}")

            except Exception as e:
                print(f"❌ Erro na linha {index + 2}: {str(e)}")
                continue

        print(f"\n✅ RESUMO ESTUDANTES:")
        print(f"   Total processados: {len(df)}")
        print(f"   Novos estudantes: {estudantes_criados}")
        print(f"   Duplicados: {estudantes_duplicados}")
        print(f"   Erros: {len(df) - estudantes_criados - estudantes_duplicados}")

        return estudantes_criados

    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {arquivo_csv}")
        return 0
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def importar_servidores(arquivo_csv, criar_usuarios=True):
    """Importa servidores de um arquivo CSV"""
    print(f"\n👥 IMPORTANDO SERVIDORES de {arquivo_csv}")
    print("=" * 50)

    try:
        df = pd.read_csv(arquivo_csv, encoding='utf-8')
        print(f"Encontradas {len(df)} linhas no arquivo")

        servidores_criados = 0
        servidores_duplicados = 0
        usuarios_criados = 0

        campus_padrao = Campus.objects.get(sigla='CREM')

        for index, row in df.iterrows():
            try:
                # Limpar e formatar os dados
                siape = str(row.get('siape', '')).strip()
                nome = str(row.get('nome', '')).strip()
                email = str(row.get('email', '')).strip().lower()
                funcao = str(row.get('funcao', '')).strip()
                membro_comissao = bool(row.get('membro_comissao_disciplinar', False))

                if not siape:
                    print(f"⚠️  Linha {index + 2}: SIAPE vazio - pulando")
                    continue

                # Verificar se já existe
                if Servidor.objects.filter(siape=siape).exists():
                    print(f"→ Já existe: {nome} ({siape})")
                    servidores_duplicados += 1
                    continue

                # Criar usuário se solicitado
                user = None
                if criar_usuarios:
                    username = siape

                    if not User.objects.filter(username=username).exists():
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=siape,  # Senha inicial = SIAPE
                            first_name=nome.split(' ')[0],
                            last_name=' '.join(nome.split(' ')[1:]) if len(nome.split(' ')) > 1 else '',
                            is_staff=True,
                            is_active=True
                        )
                        usuarios_criados += 1
                        print(f"  → Usuário criado: {username} (senha: {siape})")
                    else:
                        user = User.objects.get(username=username)

                # Criar servidor
                servidor = Servidor(
                    user=user,
                    siape=siape,
                    nome=nome,
                    funcao=funcao,
                    email=email,
                    campus=campus_padrao,
                    membro_comissao_disciplinar=membro_comissao
                )
                servidor.save()

                servidores_criados += 1
                print(f"✓ Criado: {nome} ({siape}) - {funcao}")

            except Exception as e:
                print(f"❌ Erro na linha {index + 2}: {str(e)}")
                continue

        print(f"\n✅ RESUMO SERVIDORES:")
        print(f"   Total processados: {len(df)}")
        print(f"   Novos servidores: {servidores_criados}")
        print(f"   Duplicados: {servidores_duplicados}")
        print(f"   Usuários criados: {usuarios_criados}")
        print(f"   Erros: {len(df) - servidores_criados - servidores_duplicados}")

        return servidores_criados

    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {arquivo_csv}")
        return 0
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def criar_infracoes_padrao():
    """Cria infrações padrão baseadas no regulamento disciplinar"""
    infracoes_data = [
        {
            'codigo': 'ART01-LEVE',
            'descricao': 'Descumprimento de prazos estabelecidos pela instituição',
            'gravidade': 'LEVE',
            'referencia_artigo': 'Art. 1º'
        },
        {
            'codigo': 'ART02-MEDIA',
            'descricao': 'Uso de aparelhos eletrônicos em desacordo com as regras da instituição',
            'gravidade': 'MEDIA',
            'referencia_artigo': 'Art. 2º'
        },
        {
            'codigo': 'ART03-GRAVE',
            'descricao': 'Desacato ou desrespeito a servidores, colegas ou terceiros',
            'gravidade': 'GRAVE',
            'referencia_artigo': 'Art. 3º'
        },
        {
            'codigo': 'ART04-GRAVISSIMA',
            'descricao': 'Agressão física ou moral a qualquer pessoa no ambiente institucional',
            'gravidade': 'GRAVISSIMA',
            'referencia_artigo': 'Art. 4º'
        },
        {
            'codigo': 'ART05-GRAVE',
            'descricao': 'Dano deliberado ao patrimônio da instituição',
            'gravidade': 'GRAVE',
            'referencia_artigo': 'Art. 5º'
        }
    ]

    infracoes_criadas = 0
    for infracao_data in infracoes_data:
        infracao, created = Infracao.objects.get_or_create(
            codigo=infracao_data['codigo'],
            defaults=infracao_data
        )
        if created:
            infracoes_criadas += 1
            print(f"✅ Infração criada: {infracao.codigo}")
        else:
            print(f"ℹ️  Infração já existe: {infracao.codigo}")

    return infracoes_criadas


def criar_sancoes_padrao():
    """Cria sanções padrão"""
    sancoes_data = [
        {
            'tipo': 'ADVERTENCIA_VERBAL',
            'descricao': 'Advertência verbal registrada em sistema'
        },
        {
            'tipo': 'ADVERTENCIA_ESCRITA',
            'descricao': 'Advertência por escrito com ciência do estudante'
        },
        {
            'tipo': 'SUSPENSAO',
            'descricao': 'Suspensão das atividades por período determinado'
        },
        {
            'tipo': 'TRANSFERENCIA',
            'descricao': 'Transferência compulsória de turma ou turno'
        },
        {
            'tipo': 'DESLIGAMENTO',
            'descricao': 'Desligamento da instituição'
        }
    ]

    sancoes_criadas = 0
    for sancao_data in sancoes_data:
        sancao, created = Sancao.objects.get_or_create(
            tipo=sancao_data['tipo'],
            defaults=sancao_data
        )
        if created:
            sancoes_criadas += 1
            print(f"✅ Sanção criada: {sancao.get_tipo_display()}")
        else:
            print(f"ℹ️  Sanção já existe: {sancao.get_tipo_display()}")

    return sancoes_criadas


def main():
    """Função principal para executar o carregamento completo"""
    print("🚀 INICIANDO CARREGAMENTO COMPLETO DE DADOS INICIAIS")
    print("=" * 60)

    # Configurações - AJUSTE ESTES CAMINHOS
    arquivo_responsaveis = 'responsaveis.csv'
    arquivo_estudantes = 'estudantes.csv'
    arquivo_servidores = 'servidores.csv'
    criar_usuarios_servidores = True

    try:
        # 1. Criar estrutura básica
        print("\n1. 🏛️  CRIANDO ESTRUTURA BÁSICA...")
        campus = criar_campus_padrao()
        if not campus:
            print("❌ Não foi possível criar o campus. Abortando...")
            return

        '''cursos = criar_cursos_padrao(campus)
        turmas = criar_turmas_padrao()
        infracoes = criar_infracoes_padrao()
        sancoes = criar_sancoes_padrao()'''

        # 2. Importar dados dos arquivos
        print("\n2. 📁 IMPORTANDO DADOS DOS ARQUIVOS...")

        total_responsaveis = 0
        total_estudantes = 0
        total_servidores = 0

        # Importar responsáveis
        if os.path.exists(arquivo_responsaveis):
            total_responsaveis = importar_responsaveis(arquivo_responsaveis)
        else:
            print(f"⚠️  Arquivo de responsáveis não encontrado: {arquivo_responsaveis}")

        # Importar estudantes
        if os.path.exists(arquivo_estudantes):
            total_estudantes = importar_estudantes(arquivo_estudantes)
        else:
            print(f"⚠️  Arquivo de estudantes não encontrado: {arquivo_estudantes}")

        # Importar servidores
        if os.path.exists(arquivo_servidores):
            total_servidores = importar_servidores(arquivo_servidores, criar_usuarios_servidores)
        else:
            print(f"⚠️  Arquivo de servidores não encontrado: {arquivo_servidores}")
        '''
        # Resumo final
        print("\n" + "=" * 60)
        print("🎉 CARREGAMENTO CONCLUÍDO!")
        print("📊 RESUMO GERAL:")
        print(f"   Campus: 1")
        print(f"   Cursos: {cursos}")
        print(f"   Turmas: {turmas}")
        print(f"   Infrações: {infracoes}")
        print(f"   Sanções: {sancoes}")
        print(f"   Responsáveis: {total_responsaveis}")
        print(f"   Estudantes: {total_estudantes}")
        print(f"   Servidores: {total_servidores}")
        total_registros = 1 + cursos + turmas + infracoes + sancoes + total_responsaveis + total_estudantes + total_servidores
        print(f"   TOTAL DE REGISTROS: {total_registros}")
        print("=" * 60)
        '''

    except Exception as e:
        print(f"\n❌ ERRO GERAL: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()