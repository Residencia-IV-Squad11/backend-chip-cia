"""
cron_feed_conversations.py

Lê os protocolos fechados nas tabelas do sistema de chat,
monta a fila de avaliação e processa com o Groq os itens pendentes.
Ao final, envia um e-mail com o resumo da rodada.

Fluxo:
1. Lê ChannelChatProtocol (protocolos fechados)
2. Busca as mensagens em ChannelChatMessage
3. Pega a avaliação do cliente em Avaliacao
4. Insere na avaliacao_fila com status 'pendente'
5. Processa os pendentes com o Groq
6. Envia e-mail com o resumo (total, boas, neutras, ruins, média de score)
"""

import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from config import create_app, db
from models import AvaliacaoFila
from services.groq_service import analisar_atendimento

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def buscar_protocolos_novos(conn):
    """
    Busca protocolos fechados que ainda não foram processados na fila.
    Cada protocolo vem com suas mensagens agrupadas em JSON.
    """
    sql = """
        SELECT
            p."Id"            AS protocol_id,
            p."Numero"        AS numero_protocolo,
            c."ClienteNome"   AS cliente_nome,
            c."AtendenteNome" AS atendente_nome,
            av."Nota"         AS nota,
            av."Comentario"   AS comentario,
            (
                SELECT json_agg(
                    json_build_object(
                        'remetente', m."Remetente",
                        'conteudo',  m."Conteudo",
                        'enviadaEm', m."EnviadaEm"
                    ) ORDER BY m."EnviadaEm"
                )
                FROM "ChannelChatMessage" m
                WHERE m."ProtocolId" = p."Id"
            ) AS mensagens
        FROM "ChannelChatProtocol" p
        JOIN "ChannelChat" c ON c."Id" = p."ChannelChatId"
        LEFT JOIN "Avaliacao" av ON av."ProtocolId" = p."Id"
        WHERE p."FechadoEm" IS NOT NULL
          AND p."Id" NOT IN (
              SELECT protocol_id FROM avaliacao_fila
          )
        ORDER BY p."FechadoEm" DESC
        LIMIT 50
    """
    result = conn.execute(db.text(sql))
    return result.fetchall()


def _sentimento_e_score(resultado: dict):
    """Extrai (sentimento_normalizado, score_final) de um resultado do Groq."""
    classif = resultado.get("classificacao", {}) if isinstance(resultado, dict) else {}
    qualidade = resultado.get("qualidade", {}) if isinstance(resultado, dict) else {}

    sentimento = (classif.get("sentimento") or "").strip().lower()
    if "positiv" in sentimento:
        sentimento_norm = "positivo"
    elif "negativ" in sentimento:
        sentimento_norm = "negativo"
    else:
        sentimento_norm = "neutro"

    try:
        score = float(qualidade.get("score_final", 0) or 0)
    except (TypeError, ValueError):
        score = 0.0

    return sentimento_norm, score


def processar_pendentes():
    """
    Pega itens com status 'pendente' e chama o Groq para analisar.
    Retorna um resumo da rodada com contagens por sentimento e média de score.
    """
    resumo = {
        "processadas": 0,
        "positivas": 0,
        "neutras": 0,
        "negativas": 0,
        "soma_scores": 0.0,
    }

    pendentes = AvaliacaoFila.query.filter_by(status="pendente").limit(10).all()

    if not pendentes:
        logger.info("Nenhum item pendente na fila.")
        return resumo

    logger.info("%d item(s) pendente(s) encontrado(s).", len(pendentes))

    for item in pendentes:

        if item.tentativas >= 3:
            item.status = "erro"
            db.session.commit()
            logger.warning("Protocolo %s marcado como erro após 3 tentativas.", item.numero_protocolo)
            continue

        # Marca como processando
        item.status = "processando"
        item.tentativas += 1
        db.session.commit()

        try:
            # Monta o texto da conversa para enviar ao Groq
            linhas = []
            for msg in (item.mensagens or []):
                remetente = msg.get("remetente", "Desconhecido")
                conteudo  = msg.get("conteudo", "")
                linhas.append(f"{remetente}: {conteudo}")

            texto = "\n".join(linhas)

            # Adiciona o número do protocolo e a avaliação do cliente se existir
            texto = f"Protocolo: {item.numero_protocolo}\n\n" + texto

            if item.comentario:
                texto += f"\n\nAvaliação do cliente: nota {item.nota}/10 — {item.comentario}"

            # Chama o Groq
            resultado = analisar_atendimento(texto)

            # Salva o resultado como JSON válido (aspas duplas) e marca como concluído
            item.resultado_groq = json.dumps(resultado, ensure_ascii=False)
            item.status         = "concluido"
            item.processado_em  = datetime.utcnow()
            db.session.commit()

            # Contabiliza no resumo
            sentimento, score = _sentimento_e_score(resultado)
            resumo["processadas"] += 1
            resumo["soma_scores"] += score
            if sentimento == "positivo":
                resumo["positivas"] += 1
            elif sentimento == "negativo":
                resumo["negativas"] += 1
            else:
                resumo["neutras"] += 1

            logger.info("Protocolo %s processado com sucesso.", item.numero_protocolo)

        except Exception as exc:
            # Em caso de erro, volta para pendente para tentar de novo
            item.status = "pendente"
            db.session.commit()
            logger.error("Erro ao processar protocolo %s: %s", item.numero_protocolo, exc)

    return resumo


def enviar_email_resumo(resumo: dict):
    """Envia um e-mail com o resumo da rodada do cron via Gmail SMTP."""
    remetente   = os.getenv("EMAIL_USER")
    senha       = os.getenv("EMAIL_PASS")
    destinatario = os.getenv("EMAIL_TO", remetente)

    if not remetente or not senha:
        logger.warning("EMAIL_USER ou EMAIL_PASS não configurados. E-mail não enviado.")
        return

    processadas = resumo["processadas"]

    if processadas > 0:
        media = round(resumo["soma_scores"] / processadas, 2)
    else:
        media = 0

    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    corpo = (
        f"Resumo da análise automática — {data_hoje}\n"
        f"{'=' * 40}\n\n"
        f"Conversas analisadas nesta rodada: {processadas}\n\n"
        f"  Boas (positivas):    {resumo['positivas']}\n"
        f"  Neutras:             {resumo['neutras']}\n"
        f"  Ruins (negativas):   {resumo['negativas']}\n\n"
        f"Média de score: {media}/10\n\n"
        f"{'=' * 40}\n"
        f"Chip & Cia — Análise de Atendimentos\n"
    )

    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = f"[Chip & Cia] Resumo do cron — {processadas} conversa(s) analisada(s)"
    msg["From"]    = remetente
    msg["To"]      = destinatario

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, [destinatario], msg.as_string())
        logger.info("E-mail de resumo enviado para %s.", destinatario)
    except Exception as exc:
        logger.error("Falha ao enviar e-mail: %s", exc)


def feed_conversations():
    logger.info("Cron iniciado.")
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()

        # Passo 1 — busca protocolos novos e insere na fila
        protocolos = buscar_protocolos_novos(conn)
        logger.info("%d protocolo(s) novo(s) encontrado(s).", len(protocolos))

        for row in protocolos:
            novo = AvaliacaoFila(
                protocol_id      = row.protocol_id,
                numero_protocolo = row.numero_protocolo,
                cliente_nome     = row.cliente_nome,
                atendente_nome   = row.atendente_nome,
                nota             = row.nota,
                comentario       = row.comentario,
                mensagens        = row.mensagens or [],
                status           = "pendente",
            )
            db.session.add(novo)

        db.session.commit()
        logger.info("Protocolos inseridos na fila.")

        # Passo 2 — processa os pendentes com o Groq
        resumo = processar_pendentes()

        # Passo 3 — envia o e-mail de resumo
        enviar_email_resumo(resumo)

    logger.info("Cron finalizado.")


if __name__ == "__main__":
    feed_conversations()