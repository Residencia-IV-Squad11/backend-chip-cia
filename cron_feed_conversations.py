"""
Cron Job — processa os itens pendentes na fila avaliacao_fila
enviando as conversas ao Groq para análise.

As conversas chegam nessa fila via POST /api/atendimento/receber-conversa
feito pelo sistema externo (Chip e Cia).
"""

import logging
from datetime import datetime
from config import create_app, db
from models import AvaliacaoFila
from services.groq_service import analisar_atendimento

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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

        item.status = "processando"
        item.tentativas += 1
        db.session.commit()

        try:
            linhas = []
            for msg in (item.mensagens or []):
                remetente = msg.get("remetente", "Desconhecido")
                conteudo  = msg.get("conteudo", "")
                linhas.append(f"{remetente}: {conteudo}")

            texto = "\n".join(linhas)

            if item.comentario:
                texto += f"\n\nAvaliação do cliente: nota {item.nota}/10 — {item.comentario}"

            resultado = analisar_atendimento(texto)

            item.resultado_groq = str(resultado)
            item.status         = "concluido"
            item.processado_em  = datetime.utcnow()
            db.session.commit()

            logger.info("Protocolo %s processado com sucesso.", item.numero_protocolo)

        except Exception as exc:
            item.status = "pendente"
            db.session.commit()
            logger.error("Erro ao processar protocolo %s: %s", item.numero_protocolo, exc)


def feed_conversations():
    logger.info("Cron iniciado.")
    app = create_app()

    with app.app_context():
        processar_pendentes()

    logger.info("Cron finalizado.")


if __name__ == "__main__":
    feed_conversations()