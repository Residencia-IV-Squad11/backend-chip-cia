"""
routes.py — Blueprints e endpoints da API REST.

  Blueprint: atendimento_bp  →  /api/atendimento
  Blueprint: dashboard_bp    →  /api/dashboard
"""

import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from config import db
from models import Atendimento, AvaliacaoFila, Categoria, Classificacao, Qualidade, Sentimento
from services.atendimento_service import processar_atendimento

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Blueprints
# ──────────────────────────────────────────────────────────────
atendimento_bp = Blueprint("atendimento", __name__)
dashboard_bp   = Blueprint("dashboard",   __name__)


# ──────────────────────────────────────────────────────────────
# POST /api/atendimento/receber-conversa
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/receber-conversa", methods=["POST"])
def receber_conversa():
    """
    Recebe uma conversa do sistema externo (Chip e Cia) e salva
    na fila para ser processada pelo cron com o Groq.

    Body JSON esperado:
    {
        "protocol_id": 10,
        "numero_protocolo": "2026-0001",
        "cliente_nome": "João",
        "atendente_nome": "Maria",
        "nota": 8,
        "comentario": "Ótimo atendimento",
        "mensagens": [
            {"remetente": "João", "conteudo": "Olá", "enviadaEm": "2026-01-01T10:00:00"},
            {"remetente": "Maria", "conteudo": "Olá, como posso ajudar?", "enviadaEm": "2026-01-01T10:01:00"}
        ]
    }
    """
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"sucesso": False, "erro": "Body JSON inválido ou vazio."}), 400

    # Campos obrigatórios
    protocol_id      = body.get("protocol_id")
    numero_protocolo = body.get("numero_protocolo")
    mensagens        = body.get("mensagens", [])

    if not protocol_id or not numero_protocolo:
        return jsonify({"sucesso": False, "erro": "Os campos 'protocol_id' e 'numero_protocolo' são obrigatórios."}), 400

    if not mensagens:
        return jsonify({"sucesso": False, "erro": "O campo 'mensagens' não pode estar vazio."}), 400

    # Verifica se esse protocolo já está na fila
    ja_existe = AvaliacaoFila.query.filter_by(protocol_id=protocol_id).first()
    if ja_existe:
        return jsonify({"sucesso": False, "erro": f"Protocolo {numero_protocolo} já está na fila."}), 409

    try:
        nova = AvaliacaoFila(
            protocol_id      = protocol_id,
            numero_protocolo = numero_protocolo,
            cliente_nome     = body.get("cliente_nome"),
            atendente_nome   = body.get("atendente_nome"),
            nota             = body.get("nota"),
            comentario       = body.get("comentario"),
            mensagens        = mensagens,
            status           = "pendente",
        )
        db.session.add(nova)
        db.session.commit()

        logger.info("Conversa do protocolo %s recebida e adicionada à fila.", numero_protocolo)

        return jsonify({
            "sucesso": True,
            "mensagem": f"Protocolo {numero_protocolo} adicionado à fila com sucesso.",
            "id": nova.id,
        }), 201

    except Exception as exc:
        db.session.rollback()
        logger.error("Erro ao salvar conversa na fila: %s", exc)
        return jsonify({"sucesso": False, "erro": "Erro interno ao salvar na fila."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/fila
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/fila", methods=["GET"])
def listar_fila():
    """Lista os itens da fila com seus status."""
    status = request.args.get("status")

    query = AvaliacaoFila.query

    if status:
        query = query.filter_by(status=status)

    itens = query.order_by(AvaliacaoFila.criado_em.desc()).limit(50).all()

    return jsonify({
        "sucesso": True,
        "total": len(itens),
        "itens": [
            {
                "id":               item.id,
                "protocol_id":      item.protocol_id,
                "numero_protocolo": item.numero_protocolo,
                "cliente_nome":     item.cliente_nome,
                "atendente_nome":   item.atendente_nome,
                "nota":             item.nota,
                "status":           item.status,
                "tentativas":       item.tentativas,
                "criado_em":        item.criado_em.isoformat() if item.criado_em else None,
                "processado_em":    item.processado_em.isoformat() if item.processado_em else None,
            }
            for item in itens
        ],
    }), 200


# ──────────────────────────────────────────────────────────────
# POST /api/atendimento/avaliar
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/avaliar", methods=["POST"])
def avaliar_atendimento():
    """
    Recebe o texto de uma conversa, envia ao Groq para análise
    e persiste os resultados no banco de dados.

    Body JSON esperado:
        { "texto_conversa": "..." }

    Returns 201 com { "sucesso": true, "atendimento_id": int, "score_final": float }
    """
    body = request.get_json(silent=True)

    if not body or not body.get("texto_conversa"):
        return (
            jsonify({"sucesso": False, "erro": "O campo 'texto_conversa' é obrigatório."}),
            400,
        )

    texto = body["texto_conversa"].strip()
    if len(texto) < 20:
        return (
            jsonify({"sucesso": False, "erro": "O texto da conversa é muito curto para análise."}),
            400,
        )

    try:
        resultado = processar_atendimento(texto)
        return (
            jsonify(
                {
                    "sucesso": True,
                    "atendimento_id": resultado["atendimento_id"],
                    "score_final": resultado["score_final"],
                    "mensagem": "Atendimento analisado e salvo com sucesso.",
                }
            ),
            201,
        )

    except ValueError as exc:
        logger.warning("Dados inválidos do LLM: %s", exc)
        return jsonify({"sucesso": False, "erro": str(exc)}), 422

    except RuntimeError as exc:
        logger.error("Erro na API do Groq: %s", exc)
        return jsonify({"sucesso": False, "erro": str(exc)}), 502

    except Exception as exc:
        logger.exception("Erro inesperado ao processar atendimento.")
        return jsonify({"sucesso": False, "erro": "Erro interno no servidor."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/<id>
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/<int:atendimento_id>", methods=["GET"])
def detalhe_atendimento(atendimento_id: int):
    """Retorna os detalhes completos de um atendimento pelo ID."""
    atendimento = db.session.get(Atendimento, atendimento_id)
    if not atendimento:
        return jsonify({"sucesso": False, "erro": "Atendimento não encontrado."}), 404

    return jsonify({"sucesso": True, "dados": atendimento.to_dict()}), 200


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/listar
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/listar", methods=["GET"])
def listar_atendimentos():
    """
    Lista atendimentos com paginação, trazendo os dados de
    classificação e qualidade através de JOINs.
    """
    page     = request.args.get("page",     1,  type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    paginado = (
        db.session.query(Atendimento, Qualidade, Classificacao, Categoria, Sentimento)
        .outerjoin(Qualidade, Qualidade.atendimento_id == Atendimento.idatendimento)
        .outerjoin(Classificacao, Classificacao.atendimento_id == Atendimento.idatendimento)
        .outerjoin(Categoria, Classificacao.categoria_id == Categoria.idcategoria)
        .outerjoin(Sentimento, Classificacao.sentimento_id == Sentimento.idsentimento)
        .order_by(Atendimento.data_criacao.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    atendimentos_completos = []

    for atd, qual, clas, cat, sent in paginado.items:
        atendimentos_completos.append({
            "idatendimento": atd.idatendimento,
            "resumo": atd.resumo,
            "data_criacao": atd.data_criacao.isoformat() if atd.data_criacao else None,
            "score_final": float(qual.score_final) if qual and qual.score_final else 0,
            "empatia": int(qual.empatia) if qual and qual.empatia else 0,
            "clareza": int(qual.clareza) if qual and qual.clareza else 0,
            "objetividade": int(qual.objetividade) if qual and qual.objetividade else 0,
            "resolutividade": int(qual.resolutividade) if qual and qual.resolutividade else 0,
            "categoria": cat.nome if cat else "Sem Categoria",
            "sentimento": sent.nome if sent else "Neutro"
        })

    return jsonify({
        "sucesso":    True,
        "total":      paginado.total,
        "pagina":     paginado.page,
        "paginas":    paginado.pages,
        "atendimentos": atendimentos_completos,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/resumo
# ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/resumo", methods=["GET"])
def resumo_dashboard():
    try:
        total = db.session.query(func.count(Atendimento.idatendimento)).scalar() or 0

        media_score = db.session.query(func.avg(Qualidade.score_final)).scalar()
        media_score = round(float(media_score), 2) if media_score else 0.0

        sentimento_rows = (
            db.session.query(
                Sentimento.nome,
                func.count(Classificacao.idclassificacao).label("total"),
            )
            .join(Classificacao, Classificacao.sentimento_id == Sentimento.idsentimento)
            .group_by(Sentimento.nome)
            .all()
        )
        distribuicao_sentimento = [
            {"sentimento": row.nome, "total": row.total} for row in sentimento_rows
        ]

        categoria_rows = (
            db.session.query(
                Categoria.nome,
                func.count(Classificacao.idclassificacao).label("total"),
            )
            .join(Classificacao, Classificacao.categoria_id == Categoria.idcategoria)
            .group_by(Categoria.nome)
            .order_by(func.count(Classificacao.idclassificacao).desc())
            .limit(5)
            .all()
        )
        top_categorias = [
            {"categoria": row.nome, "total": row.total} for row in categoria_rows
        ]

        evolucao_rows = (
            db.session.query(
                func.date(Atendimento.data_criacao).label("data"),
                func.round(func.avg(Qualidade.score_final), 2).label("media_score"),
                func.count(Atendimento.idatendimento).label("total"),
            )
            .join(Qualidade, Qualidade.atendimento_id == Atendimento.idatendimento)
            .group_by(func.date(Atendimento.data_criacao))
            .order_by(func.date(Atendimento.data_criacao).desc())
            .limit(30)
            .all()
        )
        evolucao_score = [
            {
                "data":        str(row.data),
                "media_score": float(row.media_score) if row.media_score else 0.0,
                "total":       row.total,
            }
            for row in reversed(evolucao_rows)
        ]

        return jsonify({
            "sucesso": True,
            "dados": {
                "total_atendimentos":      total,
                "media_score_final":       media_score,
                "distribuicao_sentimento": distribuicao_sentimento,
                "top_categorias":          top_categorias,
                "evolucao_score_diaria":   evolucao_score,
            },
        }), 200

    except Exception as exc:
        logger.exception("Erro ao gerar resumo do dashboard.")
        return jsonify({"sucesso": False, "erro": "Erro ao consultar o banco de dados."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/qualidade
# ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/qualidade", methods=["GET"])
def media_qualidade():
    """Retorna a média de cada dimensão de qualidade."""
    try:
        row = db.session.query(
            func.round(func.avg(Qualidade.empatia),        2).label("empatia"),
            func.round(func.avg(Qualidade.clareza),        2).label("clareza"),
            func.round(func.avg(Qualidade.objetividade),   2).label("objetividade"),
            func.round(func.avg(Qualidade.resolutividade), 2).label("resolutividade"),
        ).first()

        return jsonify({
            "sucesso": True,
            "dados": {
                "empatia":        float(row.empatia)        if row.empatia        else 0.0,
                "clareza":        float(row.clareza)        if row.clareza        else 0.0,
                "objetividade":   float(row.objetividade)   if row.objetividade   else 0.0,
                "resolutividade": float(row.resolutividade) if row.resolutividade else 0.0,
            },
        }), 200

    except Exception as exc:
        logger.exception("Erro ao calcular média de qualidade.")
        return jsonify({"sucesso": False, "erro": "Erro ao consultar o banco de dados."}), 500