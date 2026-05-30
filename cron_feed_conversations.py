"""
Cron Job — busca protocolos fechados nas tabelas do sistema de chat,
monta a fila de avaliação e processa com o Groq os itens pendentes.

Fluxo:
1. Lê ChannelChatProtocol (protocolos fechados)
2. Busca as mensagens em ChannelChatMessage
3. Pega a avaliação do cliente em Avaliacao
4. Insere na avaliacao_fila com status 'pendente'
5. Processa os pendentes com o Groq
"""

import logging
from datetime import datetime
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


def processar_pendentes():
    """Pega itens com status 'pendente' e chama o Groq para analisar."""
    pendentes = AvaliacaoFila.query.filter_by(status="pendente").limit(10).all()

    if not pendentes:
        logger.info("Nenhum item pendente na fila.")
        return

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

            # Salva o resultado e marca como concluído
            item.resultado_groq = str(resultado)
            item.status         = "concluido"
            item.processado_em  = datetime.utcnow()
            db.session.commit()

            logger.info("Protocolo %s processado com sucesso.", item.numero_protocolo)

        except Exception as exc:
            # Em caso de erro, volta para pendente para tentar de novo
            item.status = "pendente"
            db.session.commit()
            logger.error("Erro ao processar protocolo %s: %s", item.numero_protocolo, exc)


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
        processar_pendentes()

    logger.info("Cron finalizado.")


if __name__ == "__main__":
    feed_conversations()