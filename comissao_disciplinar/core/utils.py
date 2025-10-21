from django.core.mail import send_mail
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import qrcode
from django.conf import settings
import os

def gerar_documento_pdf(ocorrencia, tipo_documento):
    """Gera documento PDF profissional baseado no tipo"""
    buffer = BytesIO()

    # Configurar documento com margens adequadas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
        title=f"Documento - {tipo_documento} - Ocorrência #{ocorrencia.id}"
    )

    # Configurar estilos
    styles = getSampleStyleSheet()

    # Estilos personalizados baseados no design do IFB
    styles.add(ParagraphStyle(
        name='TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#006633'),  # Verde IFB
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='TituloSecundario',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#006633'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='Subtitulo',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#004a87'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='Corpo',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='Destaque',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#004a87'),
        backColor=colors.HexColor('#f0f8ff'),
        borderPadding=8,
        borderColor=colors.HexColor('#004a87'),
        borderWidth=1,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='Assinatura',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=40,
        fontName='Helvetica'
    ))

    # Elementos do documento
    elements = []

    # Cabeçalho institucional
    elements.extend(_gerar_cabecalho(styles, doc.width))

    # Linha divisória
    elements.append(Spacer(1, 10))
    elements.append(_gerar_linha_divisoria(doc.width))
    elements.append(Spacer(1, 20))

    # Conteúdo baseado no tipo de documento
    if tipo_documento == 'REGISTRO':
        elements.extend(_gerar_conteudo_registro(ocorrencia, styles, doc.width))
    elif tipo_documento == 'ATA_ADVERTENCIA':
        elements.extend(_gerar_conteudo_advertencia(ocorrencia, styles, doc.width))
    elif tipo_documento == 'NOTIFICACAO':
        elements.extend(_gerar_conteudo_notificacao(ocorrencia, styles, doc.width))
    elif tipo_documento == 'RELATORIO_FINAL':
        elements.extend(_gerar_conteudo_relatorio_final(ocorrencia, styles, doc.width))
    else:
        elements.extend(_gerar_conteudo_generico(ocorrencia, tipo_documento, styles, doc.width))

    # Rodapé
    elements.append(PageBreak())
    elements.extend(_gerar_rodape(ocorrencia, tipo_documento, styles, doc.width))

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def _gerar_cabecalho(styles, width):
    """Gera o cabeçalho institucional do IFB"""
    elements = []

    # Título principal
    elements.append(Paragraph("INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DE BRASÍLIA", styles['TituloPrincipal']))
    elements.append(Paragraph("COMISSÃO DISCIPLINAR ESTUDANTIL", styles['TituloSecundario']))

    return elements

def _gerar_linha_divisoria(width):
    """Gera uma linha divisória estilizada"""
    linha = Table([['']], colWidths=[width], rowHeights=[2])
    linha.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#006633')),
        ('BOX', (0, 0), (-1, -1), 0, colors.HexColor('#006633'))
    ]))
    return linha

def _gerar_conteudo_registro(ocorrencia, styles, width):
    """Gera conteúdo para documento de registro de ocorrência"""
    elements = []

    elements.append(Paragraph("REGISTRO DE OCORRÊNCIA DISCIPLINAR", styles['TituloSecundario']))
    elements.append(Spacer(1, 20))

    # Informações básicas da ocorrência
    info_data = [
        [Paragraph("<b>Número do Registro:</b>", styles['Corpo']),
         Paragraph(f"#{ocorrencia.id}", styles['Corpo'])],
        [Paragraph("<b>Data do Fato:</b>", styles['Corpo']),
         Paragraph(ocorrencia.data.strftime("%d/%m/%Y"), styles['Corpo'])],
        [Paragraph("<b>Horário:</b>", styles['Corpo']),
         Paragraph(ocorrencia.horario.strftime("%H:%M"), styles['Corpo'])],
        [Paragraph("<b>Status do Processo:</b>", styles['Corpo']),
         Paragraph(ocorrencia.get_status_display(), styles['Corpo'])],
        [Paragraph("<b>Registrado por:</b>", styles['Corpo']),
         Paragraph(ocorrencia.responsavel_registro.nome, styles['Corpo'])],
    ]

    info_table = Table(info_data, colWidths=[width*0.4, width*0.6])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Estudantes envolvidos
    elements.append(Paragraph("<b>ESTUDANTES ENVOLVIDOS:</b>", styles['Subtitulo']))

    estudantes_data = [['Nome', 'Matrícula', 'Turma', 'Curso']]
    for estudante in ocorrencia.estudantes.all():
        estudantes_data.append([
            Paragraph(estudante.nome, styles['Corpo']),
            Paragraph(estudante.matricula_sga, styles['Corpo']),
            Paragraph(estudante.turma.nome if estudante.turma else "N/A", styles['Corpo']),
            Paragraph(estudante.curso.nome if estudante.curso else "N/A", styles['Corpo'])
        ])

    estudantes_table = Table(estudantes_data, colWidths=[width*0.35, width*0.2, width*0.2, width*0.25])
    estudantes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#006633')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))

    elements.append(estudantes_table)
    elements.append(Spacer(1, 20))

    # Descrição detalhada
    elements.append(Paragraph("<b>DESCRIÇÃO DETALHADA DO FATO:</b>", styles['Subtitulo']))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(ocorrencia.descricao, styles['Corpo']))
    elements.append(Spacer(1, 20))

    # Infração identificada
    if ocorrencia.infracao:
        elements.append(Paragraph("<b>INFRAÇÃO IDENTIFICADA:</b>", styles['Subtitulo']))
        infracao_data = [
            [Paragraph("<b>Código:</b>", styles['Corpo']), Paragraph(ocorrencia.infracao.codigo, styles['Corpo'])],
            [Paragraph("<b>Descrição:</b>", styles['Corpo']), Paragraph(ocorrencia.infracao.descricao, styles['Corpo'])],
            [Paragraph("<b>Gravidade:</b>", styles['Corpo']), Paragraph(ocorrencia.infracao.get_gravidade_display(), styles['Corpo'])],
            [Paragraph("<b>Referência Legal:</b>", styles['Corpo']), Paragraph(ocorrencia.infracao.referencia_artigo, styles['Corpo'])],
        ]

        infracao_table = Table(infracao_data, colWidths=[width*0.3, width*0.7])
        infracao_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f8ff')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(infracao_table)
        elements.append(Spacer(1, 20))

    # Testemunhas (se houver)
    if ocorrencia.testemunhas:
        elements.append(Paragraph("<b>TESTEMUNHAS:</b>", styles['Subtitulo']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(ocorrencia.testemunhas, styles['Corpo']))
        elements.append(Spacer(1, 20))

    # Medida preventiva (se houver)
    if ocorrencia.medida_preventiva:
        elements.append(Paragraph("<b>MEDIDA PREVENTIVA ADOTADA:</b>", styles['Subtitulo']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(ocorrencia.medida_preventiva, styles['Corpo']))
        elements.append(Spacer(1, 20))

    return elements

def _gerar_conteudo_advertencia(ocorrencia, styles, width):
    """Gera conteúdo para ata de advertência"""
    elements = []

    elements.append(Paragraph("ATA DE ADVERTÊNCIA VERBAL", styles['TituloSecundario']))
    elements.append(Spacer(1, 20))

    # Informações do processo
    info_data = [
        [Paragraph("<b>Processo Nº:</b>", styles['Corpo']), Paragraph(f"#{ocorrencia.id}", styles['Corpo'])],
        [Paragraph("<b>Data:</b>", styles['Corpo']), Paragraph(datetime.now().strftime('%d/%m/%Y'), styles['Corpo'])],
        [Paragraph("<b>Local:</b>", styles['Corpo']), Paragraph("Instituto Federal de Brasília", styles['Corpo'])],
    ]

    info_table = Table(info_data, colWidths=[width*0.3, width*0.7])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Lista de estudantes
    estudantes_nomes = ", ".join([e.nome for e in ocorrencia.estudantes.all()])
    elements.append(Paragraph(f"<b>Estudante(s):</b> {estudantes_nomes}", styles['Corpo']))
    elements.append(Spacer(1, 15))

    # Texto da advertência
    texto_advertencia = f"""
    Considerando a ocorrência registrada em {ocorrencia.data.strftime('%d/%m/%Y')},
    constatou-se a prática de infração disciplinar classificada como
    <b>{ocorrencia.infracao.get_gravidade_display().lower() if ocorrencia.infracao else 'não classificada'}</b>,
    nos termos do Regulamento Discente do IFB.

    Fica registrada a presente <b>ADVERTÊNCIA VERBAL</b>, com caráter educativo e orientador,
    visando conscientizar o(s) estudante(s) sobre as normas de conduta esperadas no ambiente educacional.

    Fica o(s) estudante(s) ciente(s) de que novas ocorrências poderão acarretar em medidas disciplinares
    mais severas, conforme previsto no Regulamento Discente vigente.
    """

    elements.append(Paragraph(texto_advertencia, styles['Corpo']))
    elements.append(Spacer(1, 30))

    # Assinaturas
    elements.append(Paragraph("<b>ASSINATURAS:</b>", styles['Subtitulo']))
    elements.append(Spacer(1, 40))

    assinaturas_data = [
        ['', ''],
        ['_________________________', '_________________________'],
        [Paragraph('Servidor Registrante<br/>' + ocorrencia.responsavel_registro.nome, styles['Corpo']),
         Paragraph('Estudante(s)<br/>' + estudantes_nomes, styles['Corpo'])],
    ]

    assinaturas_table = Table(assinaturas_data, colWidths=[width*0.5, width*0.5])
    assinaturas_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(assinaturas_table)

    return elements

def _gerar_conteudo_notificacao(ocorrencia, styles, width):
    """Gera conteúdo para notificação oficial"""
    elements = []

    elements.append(Paragraph("NOTIFICAÇÃO OFICIAL", styles['TituloSecundario']))
    elements.append(Spacer(1, 20))

    # Conteúdo básico para notificação
    estudantes_nomes = ", ".join([e.nome for e in ocorrencia.estudantes.all()])

    texto_notificacao = f"""
    <b>Processo:</b> #{ocorrencia.id}
    <br/><b>Data do Fato:</b> {ocorrencia.data.strftime('%d/%m/%Y')}
    <br/><b>Estudante(s):</b> {estudantes_nomes}
    <br/><br/>
    Por meio deste documento, <b>NOTIFICA-SE</b> o(s) estudante(s) supracitado(s) sobre a abertura
    de processo disciplinar referente à ocorrência registrada.
    <br/><br/>
    Fica(m) o(s) estudante(s) ciente(s) do direito à ampla defesa e ao contraditório,
    podendo apresentar sua defesa no prazo estabelecido.
    <br/><br/>
    <b>Prazo para Defesa:</b> {ocorrencia.prazo_defesa.strftime('%d/%m/%Y') if ocorrencia.prazo_defesa else 'A definir'}
    """

    elements.append(Paragraph(texto_notificacao, styles['Corpo']))
    elements.append(Spacer(1, 30))

    return elements

def _gerar_conteudo_relatorio_final(ocorrencia, styles, width):
    """Gera conteúdo para relatório final"""
    elements = []

    elements.append(Paragraph("RELATÓRIO FINAL DO PROCESSO DISCIPLINAR", styles['TituloSecundario']))
    elements.append(Spacer(1, 20))

    # Conteúdo básico para relatório final
    texto_relatorio = f"""
    <b>Processo Nº:</b> #{ocorrencia.id}
    <br/><b>Data de Conclusão:</b> {datetime.now().strftime('%d/%m/%Y')}
    <br/><b>Status Final:</b> {ocorrencia.get_status_display()}
    <br/><br/>
    Este relatório apresenta a conclusão do processo disciplinar instaurado para apuração dos fatos.
    <br/><br/>
    <b>Decisão Final:</b> Processo {ocorrencia.get_status_display().lower()} com base nas evidências e análise realizada.
    """

    elements.append(Paragraph(texto_relatorio, styles['Corpo']))
    elements.append(Spacer(1, 30))

    return elements

def _gerar_conteudo_generico(ocorrencia, tipo_documento, styles, width):
    """Gera conteúdo para tipos de documento não especificados"""
    elements = []

    elements.append(Paragraph(f"DOCUMENTO: {tipo_documento}", styles['TituloSecundario']))
    elements.append(Spacer(1, 20))

    texto_generico = f"""
    <b>Processo:</b> #{ocorrencia.id}
    <br/><b>Data do Fato:</b> {ocorrencia.data.strftime('%d/%m/%Y')}
    <br/><b>Status:</b> {ocorrencia.get_status_display()}
    <br/><br/>
    Documento gerado para registro institucional.
    """

    elements.append(Paragraph(texto_generico, styles['Corpo']))

    return elements

def _gerar_rodape(ocorrencia, tipo_documento, styles, width):
    """Gera rodapé com informações de autenticação"""
    elements = []

    elements.append(Spacer(1, 20))
    elements.append(_gerar_linha_divisoria(width))
    elements.append(Spacer(1, 10))

    # Informações do rodapé
    rodape_texto = f"""
    Documento gerado automaticamente pelo Sistema de Ocorrências IFB em {datetime.now().strftime('%d/%m/%Y às %H:%M')} |
    Processo #{ocorrencia.id} | Tipo: {tipo_documento} |
    Comissão Disciplinar Estudantil - Instituto Federal de Brasília
    """

    elements.append(Paragraph(rodape_texto, styles['Rodape']))

    return elements


def enviar_notificacao_email(notificacao_id):
    """Envio síncrono de notificações por e-mail (sem Celery)"""
    from .models import NotificacaoOficial

    try:
        notificacao = NotificacaoOficial.objects.get(id=notificacao_id)
        destinatarios = [email.strip() for email in notificacao.destinatarios.split(',')]

        send_mail(
            subject=f"IFB - {notificacao.get_tipo_display()}",
            message=notificacao.texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )

        return f"E-mail enviado para {len(destinatarios)} destinatário(s)"
    except Exception as e:
        return f"Erro ao enviar e-mail: {str(e)}"