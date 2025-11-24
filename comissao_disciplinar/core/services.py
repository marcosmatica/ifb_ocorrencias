# core/services.py - Versão com prioridade MÃE/PAI para SMS
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notificacao, PreferenciaNotificacao
import requests
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ServicoNotificacao:
    """Serviço centralizado para envio de notificações"""

    @staticmethod
    def _get_debug_destinatarios():
        """Retorna destinatários para modo DEBUG"""
        if getattr(settings, 'DEBUG', False):
            return {
                'email': 'marcos.rodrigues@ifb.edu.br',
                'sms': '981564098'
            }
        return None

    @staticmethod
    def notificar_responsaveis_ocorrencia(ocorrencia, tipo_ocorrencia='ocorrencia'):
        """
        Notifica responsáveis via email e SMS sobre ocorrências
        """
        print(f"\n{'=' * 60}")
        print(f" INICIANDO NOTIFICAÇÃO DOS RESPONSÁVEIS")
        print(f"{'=' * 60}")
        print(f" Ocorrência ID: {ocorrencia.id}")
        print(f" Tipo: {tipo_ocorrencia}")
        print(f" DEBUG: {getattr(settings, 'DEBUG', False)}")

        # Coletar responsáveis únicos
        responsaveis_unicos = {}
        estudantes = ocorrencia.estudantes.all()
        print(f" Total de estudantes: {estudantes.count()}")

        for estudante in estudantes:
            print(f"\n Estudante: {estudante.nome}")
            print(f"   Matrícula: {estudante.matricula_sga}")

            responsaveis = estudante.responsaveis.all()
            print(f"   Responsáveis cadastrados: {responsaveis.count()}")

            for responsavel in responsaveis:
                print(f"\n   📋 Responsável: {responsavel.nome}")
                print(f"      Email: {responsavel.email}")
                print(f"      Celular: {responsavel.celular}")
                print(f"      Preferência: {responsavel.get_preferencia_contato_display()}")

                if responsavel.id not in responsaveis_unicos:
                    responsaveis_unicos[responsavel.id] = {
                        'responsavel': responsavel,
                        'estudantes': []
                    }
                responsaveis_unicos[responsavel.id]['estudantes'].append(estudante)

        print(f"\n Total de responsáveis únicos: {len(responsaveis_unicos)}")

        # Enviar notificações
        for resp_id, resp_data in responsaveis_unicos.items():
            responsavel = resp_data['responsavel']
            estudantes_lista = resp_data['estudantes']

            print(f"\n{'=' * 60}")
            print(f" Processando responsável: {responsavel.nome}")
            print(f"{'=' * 60}")

            # Email
            try:
                print(f"\n Tentando enviar EMAIL...")
                ServicoNotificacao._enviar_email_responsavel(
                    responsavel, estudantes_lista, ocorrencia, tipo_ocorrencia
                )
            except Exception as e:
                print(f" ERRO ao enviar email: {str(e)}")
                import traceback
                traceback.print_exc()

        # SMS: Enviar apenas uma vez por estudante, priorizando MÃE
        print(f"\n{'=' * 60}")
        print(f" INICIANDO ENVIO DE SMS COM PRIORIDADE")
        print(f"{'=' * 60}")

        for estudante in estudantes:
            print(f"\n Processando SMS para estudante: {estudante.nome}")
            ServicoNotificacao._enviar_sms_priorizado(estudante, ocorrencia, tipo_ocorrencia)

        print(f"\n{'=' * 60}")
        print(f" PROCESSO DE NOTIFICAÇÃO CONCLUÍDO")
        print(f"{'=' * 60}\n")

    @staticmethod
    def _enviar_sms_priorizado(estudante, ocorrencia, tipo_ocorrencia):
        """
        Envia SMS priorizando MÃE, depois PAI
        """
        print(f"\n Buscando responsáveis para SMS...")

        responsaveis = estudante.responsaveis.all()

        # Separar por tipo de parentesco
        mae = None
        pai = None
        outros = []

        for resp in responsaveis:
            if resp.preferencia_contato not in ['CELULAR', 'WHATSAPP', 'E-mail', 'EMAIL', 'Email']:
                continue

            parentesco_upper = resp.tipo_vinculo.upper() if resp.tipo_vinculo else ''

            if 'MÃE' in parentesco_upper or 'MAE' in parentesco_upper:
                mae = resp
                print(f"   Encontrada MÃE: {resp.nome}")
            elif 'PAI' in parentesco_upper:
                pai = resp
                print(f"   Encontrado PAI: {resp.nome}")
            else:
                outros.append(resp)
                print(f"   Encontrado OUTRO: {resp.nome} ({resp.tipo_vinculo})")

        # Tentar enviar na ordem: MÃE -> PAI -> OUTROS
        ordem_envio = []
        if mae:
            ordem_envio.append(mae)
        if pai:
            ordem_envio.append(pai)
        ordem_envio.extend(outros)

        if not ordem_envio:
            print(f"   Nenhum responsável com preferência SMS/WhatsApp")
            return

        print(f"\n Ordem de tentativa: {[r.nome for r in ordem_envio]}")

        # Tentar enviar até conseguir
        for responsavel in ordem_envio:
            try:
                print(f"\n Tentando enviar SMS para {responsavel.nome} ({responsavel.tipo_vinculo})...")
                sucesso = ServicoNotificacao._enviar_sms_responsavel(
                    responsavel, [estudante], ocorrencia, tipo_ocorrencia
                )

                if sucesso:
                    print(f"    SMS enviado com SUCESSO para {responsavel.nome}")
                    return  # Parar após primeiro envio bem-sucedido
                else:
                    print(f"    Falha ao enviar para {responsavel.nome}, tentando próximo...")

            except Exception as e:
                print(f"    ERRO ao enviar para {responsavel.nome}: {str(e)}")
                continue

        print(f"\n ⚠️  Não foi possível enviar SMS para nenhum responsável")

    @staticmethod
    def _enviar_email_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia='ocorrencia'):
        """Envia email para responsável - ATUALIZADO para múltiplos tipos"""
        print(f"\n{'=' * 60}")
        print(f" _enviar_email_responsavel")
        print(f"{'=' * 60}")
        print(f" Responsável: {responsavel.nome}")
        print(f" Email: {responsavel.email}")
        print(f" Preferência: {responsavel.get_preferencia_contato_display()}")

        try:
            if responsavel.preferencia_contato not in ['E-mail', 'CELULAR', 'EMAIL', 'Email']:
                print(f"  Preferência não é EMAIL/WHATSAPP - Pulando")
                return

            # Verificar configurações de email
            print(f"\n Verificando configurações de email...")

            # Formatar informações dos estudantes
            estudantes_info = []
            for estudante in estudantes:
                primeiro_nome = estudante.nome.split()[0] if estudante.nome else "Estudante"
                nome_abreviado = primeiro_nome + " ..."
                matricula_abreviada = estudante.matricula_sga
                estudantes_info.append(f"{nome_abreviado} ({matricula_abreviada})")

            estudantes_str = ", ".join(estudantes_info)
            print(f"   Estudantes: {estudantes_str}")

            # Definir templates baseados no tipo de ocorrência
            if tipo_ocorrencia == 'ocorrencia_rapida':
                template_html = 'email/notificacao_responsavel_rapida.html'
                template_text = 'email/notificacao_responsavel_rapida.txt'
                assunto = f"[IFB] Registro - {estudantes_str}"
            else:
                template_html = 'email/notificacao_responsavel_ocorrencia.html'
                template_text = 'email/notificacao_responsavel_ocorrencia.txt'
                assunto = f"[IFB] Registro Disciplinar - {estudantes_str}"

            print(f"\n Templates:")
            print(f"   HTML: {template_html}")
            print(f"   TEXT: {template_text}")
            print(f"   Assunto: {assunto}")

            # NOVO: Preparar informações dos tipos para o contexto
            if tipo_ocorrencia == 'ocorrencia_rapida' and hasattr(ocorrencia, 'tipos_rapidos'):
                tipos_lista = list(ocorrencia.tipos_rapidos.all())
                tipos_str = "; ".join([tipo.descricao for tipo in tipos_lista])
                tipos_count = len(tipos_lista)
            else:
                tipos_lista = []
                tipos_str = ocorrencia.get_tipo_rapido_display() if hasattr(ocorrencia,
                                                                            'get_tipo_rapido_display') else "Registro"
                tipos_count = 1

            contexto = {
                'responsavel': responsavel,
                'estudantes': estudantes,
                'estudantes_str': estudantes_str,
                'ocorrencia': ocorrencia,
                'tipo_ocorrencia': tipo_ocorrencia,
                # NOVOS CAMPOS para múltiplos tipos
                'tipos_lista': tipos_lista,
                'tipos_str': tipos_str,
                'tipos_count': tipos_count,
            }

            print(f"\n Contexto preparado:")
            print(f"   Tipos count: {tipos_count}")
            print(f"   Tipos str: {tipos_str}")

            print(f"\n Renderizando templates...")
            try:
                mensagem_html = render_to_string(template_html, contexto)
                mensagem_texto = render_to_string(template_text, contexto)
                print(f"    Templates renderizados")
                print(f"   HTML length: {len(mensagem_html)} chars")
                print(f"   TEXT length: {len(mensagem_texto)} chars")
            except Exception as e:
                print(f"    ERRO ao renderizar templates: {str(e)}")
                raise

            print(f"\n Criando email...")

            # VERIFICAÇÃO DEBUG - USAR EMAIL ESPECÍFICO SE DEBUG=True
            debug_destinatarios = ServicoNotificacao._get_debug_destinatarios()
            if debug_destinatarios:
                destinatario_email = debug_destinatarios['email']
                print(f"   ⚠️  MODO DEBUG - Email enviado para: {destinatario_email}")
            else:
                destinatario_email = responsavel.email
                print(f"   Destinatário: {destinatario_email}")

            email = EmailMultiAlternatives(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                [destinatario_email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            print(f"    Email criado")

            print(f"\n Enviando email...")
            email.send()
            print(f"    Email enviado com SUCESSO!")

            logger.info(f" Email enviado para {responsavel.nome} ({destinatario_email})")

        except Exception as e:
            print(f"\n ERRO FATAL ao enviar email:")
            print(f"   {str(e)}")
            logger.error(f" Erro ao enviar email para {responsavel.nome}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _enviar_sms_responsavel(responsavel, estudantes, ocorrencia, tipo_ocorrencia):
        """
        Envia SMS para responsável - ATUALIZADO para múltiplos tipos

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        print(f"\n{'=' * 60}")
        print(f" _enviar_sms_responsavel")
        print(f"{'=' * 60}")
        print(f" Responsável: {responsavel.nome}")
        print(f" Celular: {responsavel.celular}")
        print(f" Preferência: {responsavel.get_preferencia_contato_display()}")

        try:
            if responsavel.preferencia_contato not in ['CELULAR', 'WHATSAPP', 'E-mail', 'EMAIL', 'Email']:
                print(f"  Preferência não é CELULAR/WHATSAPP - Pulando")
                return False

            # Verificar configuração Twilio
            print(f"\n Verificando configurações Twilio...")
            has_twilio = hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN') and hasattr(
                settings, 'TWILIO_PHONE_NUMBER')

            if not has_twilio:
                print(f"     Twilio não configurado")
                return False

            # FORMATAR MENSAGEM - ATUALIZADO para múltiplos tipos
            print(f"\n Formatando mensagem...")
            if len(estudantes) == 1:
                estudante = estudantes[0]
                primeiro_nome = estudante.nome.split()[0] if estudante.nome else "Estudante"
                estudantes_info = f"{primeiro_nome} ({estudante.matricula_sga})"
            else:
                estudantes_info = f"{len(estudantes)} estudantes"

            # Formatar email para exibição (com asteriscos)
            parte_local, dominio = responsavel.email.split('@')
            parte_local_ = parte_local[:5] + '*' * (len(parte_local) - 5)
            texto_email = parte_local_ + '@' + dominio

            # NOVO: Formatar tipos para SMS
            if tipo_ocorrencia == 'ocorrencia_rapida' and hasattr(ocorrencia, 'tipos_rapidos'):
                tipos = list(ocorrencia.tipos_rapidos.all())
                if len(tipos) == 1:
                    tipo_display = tipos[0].codigo
                elif len(tipos) == 2:
                    tipo_display = f"{tipos[0].codigo} e {tipos[1].codigo}"
                else:
                    tipo_display = f"{tipos[0].codigo} e outros"
            else:
                # Fallback para o sistema antigo
                tipo_display = getattr(ocorrencia, 'get_tipo_rapido_display', lambda: 'Registro')()
                if callable(tipo_display):
                    tipo_display = tipo_display()

            # Criar mensagem baseada no tipo de ocorrência
            if tipo_ocorrencia == 'ocorrencia_rapida':
                mensagem = (
                    f"IFB Recanto das Emas - Ocorrência pedagógica do(s) tipo(s)- {tipo_display}. Estudante {estudantes_info} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y %H:%M')}. "
                    f"Consulte o email {texto_email} para maiores detalhes."
                )
            else:
                mensagem = (
                    f"IFB - Registro disciplinar envolvendo {estudantes_info} "
                    f"em {ocorrencia.data.strftime('%d/%m/%Y')}. "
                    f"Consulte o email {texto_email} para detalhes."
                )

            print(f"\n Mensagem formatada: {mensagem}")

            # VERIFICAÇÃO DEBUG - USAR NÚMERO ESPECÍFICO SE DEBUG=True
            debug_destinatarios = ServicoNotificacao._get_debug_destinatarios()
            if debug_destinatarios:
                numero_envio = debug_destinatarios['sms']
                print(f"   ⚠️  MODO DEBUG - SMS enviado para: {numero_envio}")
            else:
                numero_envio = responsavel.celular
                print(f"   Número para envio: {numero_envio}")

            # Enviar via Twilio
            print(f"\n Enviando SMS via Twilio...")
            sucesso = ServicoNotificacao._enviar_sms_via_twilio(numero_envio, mensagem)
            return sucesso

        except Exception as e:
            print(f"\n ERRO ao enviar SMS:")
            print(f"   {str(e)}")
            logger.error(f" Erro ao enviar SMS para {responsavel.nome}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _enviar_sms_via_twilio(numero, mensagem):
        """
        Envia SMS via Twilio

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        print(f"\n{'=' * 60}")
        print(f" _enviar_sms_via_twilio")
        print(f"{'=' * 60}")
        print(f" Número: {numero}")
        print(f" Mensagem: {mensagem}")

        try:
            if not hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                print("  Twilio não configurado - settings.TWILIO_ACCOUNT_SID não existe")
                return False

            print(f"\n Importando Twilio Client...")
            from twilio.rest import Client

            print(f" Criando cliente Twilio...")
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            print(f"    Cliente criado")

            # Padronizar número antes do envio
            numero_padronizado = ServicoNotificacao._padronizar_numero_telefone(numero)
            if not numero_padronizado:
                print(f"  Número {numero} não pôde ser padronizado para envio SMS")
                return False

            print(f" Número padronizado: {numero_padronizado}")

            print(f"\n Enviando mensagem...")
            print(f"   De: {settings.TWILIO_PHONE_NUMBER}")
            print(f"   Para: {numero_padronizado}")

            message = client.messages.create(
                body=mensagem,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=numero_padronizado
            )

            print(f"    SMS enviado com SUCESSO!")
            print(f"   SID: {message.sid}")
            print(f"   Status: {message.status}")

            logger.info(f" SMS Twilio enviado para {numero_padronizado}: {message.sid}")
            return True

        except Exception as e:
            print(f"\n ERRO FATAL no Twilio:")
            print(f"   {str(e)}")
            logger.error(f" Erro Twilio: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _padronizar_numero_telefone(numero):
        """
        Padroniza número de telefone para o formato Twilio (E.164)

        Args:
            numero (str): Número de telefone a ser padronizado

        Returns:
            str: Número padronizado no formato E.164 ou None se não for possível padronizar
        """
        print(f"\n Padronizando número: {numero}")

        # Remover todos os caracteres não numéricos
        numero_limpo = ''.join(filter(str.isdigit, str(numero)))
        print(f"   Número limpo: {numero_limpo}")

        # Verificar se é um número válido
        if not numero_limpo:
            print("   Número vazio após limpeza")
            return None

        # Verificar se é telefone fixo (começa com 3)
        if numero_limpo[0] == '3':
            print("   Número é telefone fixo (começa com 3) - não é possível enviar SMS")
            return None

        # Adicionar DDD 61 se não tiver
        if len(numero_limpo) == 8:
            numero_com_ddd = '61' + numero_limpo
            print(f"   Adicionado DDD 61: {numero_com_ddd}")
        elif len(numero_limpo) == 9:
            numero_com_ddd = '61' + numero_limpo
            print(f"   Adicionado DDD 61: {numero_com_ddd}")
        elif len(numero_limpo) == 10:
            # Já tem DDD, verificar se é 61
            ddd = numero_limpo[:2]
            if ddd != '61':
                print(f"   DDD {ddd} diferente de 61 - mantendo mesmo assim")
            numero_com_ddd = numero_limpo
        elif len(numero_limpo) == 11:
            # Já tem DDD + 9, verificar se DDD é 61
            ddd = numero_limpo[:2]
            if ddd != '61':
                print(f"   DDD {ddd} diferente de 61 - mantendo mesmo assim")
            numero_com_ddd = numero_limpo
        else:
            print(f"   Número com formato inválido: {len(numero_limpo)} dígitos")
            return None

        # Adicionar o 9 na frente se necessário (número tem 10 dígitos = DDD + 8)
        if len(numero_com_ddd) == 10:
            numero_com_9 = '9' + numero_com_ddd
            print(f"   Adicionado dígito 9: {numero_com_9}")
        else:
            numero_com_9 = numero_com_ddd

        # Verificar se o número tem 11 dígitos (DDD + 9 dígitos)
        if len(numero_com_9) != 11:
            print(f"   Número não padronizável: {len(numero_com_9)} dígitos")
            return None

        # Adicionar código do país Brasil (+55)
        numero_final = '+55' + numero_com_9
        print(f"   Número final padronizado: {numero_final}")

        return numero_final

    @staticmethod
    def notificar_nova_ocorrencia(ocorrencia):
        """Notifica comissão sobre nova ocorrência"""
        print(f"\n{'=' * 60}")
        print(f" NOTIFICANDO COMISSÃO")
        print(f"{'=' * 60}")

        from .models import Servidor

        membros_comissao = Servidor.objects.filter(membro_comissao_disciplinar=True)
        print(f" Membros da comissão: {membros_comissao.count()}")

        for servidor in membros_comissao:
            print(f"\n Notificando: {servidor.nome}")

            prioridade = 'ALTA' if (
                    ocorrencia.infracao and
                    ocorrencia.infracao.gravidade in ['GRAVE', 'GRAVISSIMA']
            ) else 'MEDIA'

            print(f"   Prioridade: {prioridade}")

            try:
                ServicoNotificacao.criar_notificacao(
                    usuario=servidor.user,
                    tipo='NOVA_OCORRENCIA',
                    titulo=f'Nova Ocorrência #{ocorrencia.id}',
                    mensagem=f'Registrada por {ocorrencia.responsavel_registro.nome}',
                    ocorrencia=ocorrencia,
                    prioridade=prioridade
                )
                print(f"    Notificação criada")
            except Exception as e:
                print(f"    ERRO: {str(e)}")

    @staticmethod
    def criar_notificacao(usuario, tipo, titulo, mensagem, ocorrencia=None, prioridade='MEDIA'):
        """Cria notificação in-app"""
        print(f"\n Criando notificação in-app...")
        print(f"   Usuário: {usuario.username}")
        print(f"   Tipo: {tipo}")
        print(f"   Título: {titulo}")

        notificacao = Notificacao.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            ocorrencia=ocorrencia,
            prioridade=prioridade
        )
        print(f"    Notificação #{notificacao.id} criada")

        if prioridade in ['ALTA', 'URGENTE']:
            print(f"    Enviando email (prioridade {prioridade})...")
            ServicoNotificacao.enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia)

        return notificacao

    @staticmethod
    def enviar_notificacao_email(usuario, titulo, mensagem, ocorrencia=None):
        """Envia notificação por email"""
        print(f"\n Enviando notificação email...")
        print(f"   Para: {usuario.email}")

        try:
            preferencias = PreferenciaNotificacao.objects.get(usuario=usuario)
            if not preferencias.receber_notificacoes_urgentes:
                print(f"     Usuário desativou notificações urgentes")
                return
        except PreferenciaNotificacao.DoesNotExist:
            print(f"     Criando preferências padrão")
            PreferenciaNotificacao.objects.create(usuario=usuario)

        assunto = f"[Sistema Ocorrências IFB] {titulo}"
        contexto = {
            'titulo': titulo,
            'mensagem': mensagem,
            'ocorrencia': ocorrencia,
            'usuario': usuario
        }

        mensagem_html = render_to_string('email/notificacao_urgente.html', contexto)
        mensagem_texto = render_to_string('email/notificacao_urgente.txt', contexto)

        # VERIFICAÇÃO DEBUG - USAR EMAIL ESPECÍFICO SE DEBUG=True
        debug_destinatarios = ServicoNotificacao._get_debug_destinatarios()
        if debug_destinatarios:
            destinatario_email = debug_destinatarios['email']
            print(f"   ⚠️  MODO DEBUG - Email enviado para: {destinatario_email}")
        else:
            destinatario_email = usuario.email
            print(f"   Destinatário: {destinatario_email}")

        try:
            email = EmailMultiAlternatives(
                assunto,
                mensagem_texto,
                settings.DEFAULT_FROM_EMAIL,
                [destinatario_email]
            )
            email.attach_alternative(mensagem_html, "text/html")
            email.send()
            print(f"    Email enviado para {destinatario_email}")
            logger.info(f" Email enviado para {destinatario_email}")
        except Exception as e:
            print(f"    ERRO: {str(e)}")
            logger.error(f" Erro ao enviar email: {e}")