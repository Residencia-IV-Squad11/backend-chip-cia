"""
routes.py — Blueprints e endpoints da API REST.

  Blueprint: atendimento_bp  →  /api/atendimento
  Blueprint: dashboard_bp    →  /api/dashboard
"""

import logging
import httpx
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from config import db
from models import Atendimento, Categoria, Classificacao, Qualidade, Sentimento
from services.atendimento_service import processar_atendimento

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Blueprints
# ──────────────────────────────────────────────────────────────
atendimento_bp = Blueprint("atendimento", __name__)
dashboard_bp   = Blueprint("dashboard",   __name__)


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

    external_id = body.get("external_id")

    try:
        resultado = processar_atendimento(texto, external_id=external_id)
        status_code = 201 if resultado.get("created", True) else 200
        mensagem = (
            "Atendimento analisado e salvo com sucesso."
            if resultado.get("created", True)
            else "Atendimento externo já processado anteriormente."
        )

        return (
            jsonify(
                {
                    "sucesso": True,
                    "atendimento_id": resultado["atendimento_id"],
                    "score_final": resultado["score_final"],
                    "mensagem": mensagem,
                }
            ),
            status_code,
        )

    except ValueError as exc:
        logger.warning("Dados inválidos do LLM: %s", exc)
        return jsonify({"sucesso": False, "erro": str(exc)}), 422

    except EnvironmentError as exc:
        logger.error("Erro de configuração do Groq: %s", exc)
        return jsonify({"sucesso": False, "erro": str(exc)}), 500

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


def _criar_atendimento_a_partir_da_api_externa(protocolo: str, dados: dict) -> Atendimento:
    texto = dados.get("texto") or dados.get("descricao") or dados.get("mensagem") or ""
    resumo = dados.get("resumo") or (texto[:200] if texto else None)

    return Atendimento(
        protocolo=protocolo,
        texto=texto,
        resumo=resumo,
    )


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/importar/<protocolo>
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/importar/<string:protocolo>", methods=["GET"])
def importar_atendimento(protocolo: str):
    """Importa um atendimento de uma API externa pelo protocolo e salva no banco."""
    external_url = f"https://api.externa.com/atendimento/{protocolo}"

    try:
        response = httpx.get(external_url, timeout=10)
    except httpx.RequestError as exc:
        logger.error("Falha ao conectar na API externa: %s", exc)
        return jsonify({"sucesso": False, "erro": "Não foi possível consultar a API externa."}), 400

    if response.status_code != 200:
        return jsonify({"sucesso": False, "erro": "API externa retornou status inválido."}), 400

    try:
        dados_externos = response.json()
    except ValueError:
        return jsonify({"sucesso": False, "erro": "Resposta da API externa não é JSON válido."}), 400

    if not isinstance(dados_externos, dict):
        return jsonify({"sucesso": False, "erro": "Resposta da API externa não contém um objeto JSON."}), 400

    try:
        atendimento = _criar_atendimento_a_partir_da_api_externa(protocolo, dados_externos)
        db.session.add(atendimento)
        db.session.commit()

        return jsonify({"sucesso": True, "dados": atendimento.to_dict()}), 201
    except Exception as exc:
        logger.exception("Erro ao salvar atendimento importado.")
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": "Erro interno ao salvar atendimento."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/protocolo/<protocolo>
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/protocolo/<string:protocolo>", methods=["GET"])
def consultar_atendimento_por_protocolo(protocolo: str):
    atendimento = Atendimento.query.filter_by(protocolo=protocolo).first()
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

    # Fazemos um JOIN explícito para garantir que todas as métricas vão para o frontend
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
    
    # Extraímos os dados das múltiplas tabelas para um único dicionário plano
    for atd, qual, clas, cat, sent in paginado.items:
        atendimentos_completos.append({
            "idatendimento": atd.idatendimento,
            "resumo": atd.resumo,
            "data_criacao": atd.data_criacao.isoformat() if atd.data_criacao else None,
            # Se houver qualidade, enviamos os scores, senão enviamos 0
            "score_final": float(qual.score_final) if qual and qual.score_final else 0,
            "empatia": int(qual.empatia) if qual and qual.empatia else 0,
            "clareza": int(qual.clareza) if qual and qual.clareza else 0,
            "objetividade": int(qual.objetividade) if qual and qual.objetividade else 0,
            "resolutividade": int(qual.resolutividade) if qual and qual.resolutividade else 0,
            # Se houver classificação, enviamos os nomes, senão enviamos um valor padrão
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
# POST /api/atendimento/validar
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/validar", methods=["POST"])
def validar_atendimento():
    """Valida um texto de atendimento e retorna informações básicas."""
    body = request.get_json(silent=True)

    if not body or not body.get("texto"):
        return jsonify({"sucesso": False, "erro": "O campo 'texto' é obrigatório."}), 400

    texto = str(body["texto"]).strip()
    return jsonify({
        "sucesso": True,
        "texto_original": texto,
        "tamanho": len(texto),
        "mensagem": "Texto recebido com sucesso.",
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/resumo
# ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/resumo", methods=["GET"])
def resumo_dashboard():
    """
    Agrega informações para alimentar o dashboard:
      - total de atendimentos
      - média do score_final
      - distribuição de sentimento
      - top 5 categorias mais frequentes
    """
    try:
        # Total de atendimentos
        total = db.session.query(func.count(Atendimento.idatendimento)).scalar() or 0

        # Média geral do score_final
        media_score = (
            db.session.query(func.avg(Qualidade.score_final)).scalar()
        )
        media_score = round(float(media_score), 2) if media_score else 0.0

        # Distribuição de sentimento
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

        # Top 5 categorias
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

        # Evolução de score por dia (últimos 30 registros)
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
    """Retorna a média de cada dimensão de qualidade (empatia, clareza, etc.)."""
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
