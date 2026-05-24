"""
routes.py — Blueprints e endpoints da API REST.
"""

import json
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from config import db
from models import Atendimento, AvaliacaoFila, Categoria, Classificacao, Qualidade, Sentimento
from services.atendimento_service import processar_atendimento

logger = logging.getLogger(__name__)

atendimento_bp = Blueprint("atendimento", __name__)
dashboard_bp   = Blueprint("dashboard",   __name__)


# ──────────────────────────────────────────────────────────────
# POST /api/atendimento/receber-conversa
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/receber-conversa", methods=["POST"])
def receber_conversa():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"sucesso": False, "erro": "Body JSON inválido."}), 400

    protocol_id      = body.get("protocol_id")
    numero_protocolo = body.get("numero_protocolo")
    mensagens        = body.get("mensagens", [])

    if not protocol_id or not numero_protocolo:
        return jsonify({"sucesso": False, "erro": "protocol_id e numero_protocolo são obrigatórios."}), 400

    if not mensagens:
        return jsonify({"sucesso": False, "erro": "mensagens não pode estar vazio."}), 400

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
        return jsonify({"sucesso": True, "mensagem": f"Protocolo {numero_protocolo} adicionado.", "id": nova.id}), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": "Erro interno."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/fila
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/fila", methods=["GET"])
def listar_fila():
    status = request.args.get("status")
    query  = AvaliacaoFila.query
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
                "resultado_groq":   item.resultado_groq,
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
    body = request.get_json(silent=True)
    if not body or not body.get("texto_conversa"):
        return jsonify({"sucesso": False, "erro": "O campo 'texto_conversa' é obrigatório."}), 400

    texto = body["texto_conversa"].strip()
    if len(texto) < 20:
        return jsonify({"sucesso": False, "erro": "Texto muito curto."}), 400

    try:
        resultado = processar_atendimento(texto)
        return jsonify({"sucesso": True, "atendimento_id": resultado["atendimento_id"], "score_final": resultado["score_final"]}), 201
    except ValueError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), 422
    except RuntimeError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), 502
    except Exception:
        return jsonify({"sucesso": False, "erro": "Erro interno."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/<id>
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/<int:atendimento_id>", methods=["GET"])
def detalhe_atendimento(atendimento_id: int):
    atendimento = db.session.get(Atendimento, atendimento_id)
    if not atendimento:
        return jsonify({"sucesso": False, "erro": "Não encontrado."}), 404
    return jsonify({"sucesso": True, "dados": atendimento.to_dict()}), 200


# ──────────────────────────────────────────────────────────────
# GET /api/atendimento/listar
# ──────────────────────────────────────────────────────────────
@atendimento_bp.route("/listar", methods=["GET"])
def listar_atendimentos():
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
            "resumo":        atd.resumo,
            "data_criacao":  atd.data_criacao.isoformat() if atd.data_criacao else None,
            "score_final":   float(qual.score_final) if qual and qual.score_final else 0,
            "empatia":       int(qual.empatia)        if qual and qual.empatia    else 0,
            "clareza":       int(qual.clareza)        if qual and qual.clareza    else 0,
            "objetividade":  int(qual.objetividade)   if qual and qual.objetividade else 0,
            "resolutividade":int(qual.resolutividade) if qual and qual.resolutividade else 0,
            "categoria":     cat.nome  if cat  else "Sem Categoria",
            "sentimento":    sent.nome if sent else "Neutro"
        })

    return jsonify({
        "sucesso": True, "total": paginado.total,
        "pagina": paginado.page, "paginas": paginado.pages,
        "atendimentos": atendimentos_completos,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/resumo  ← lê da avaliacao_fila
# ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/resumo", methods=["GET"])
def resumo_dashboard():
    try:
        # Busca todos os itens concluídos
        concluidos = AvaliacaoFila.query.filter_by(status="concluido").all()

        total = len(concluidos)
        scores = []
        sentimentos = {"Positivo": 0, "Neutro": 0, "Negativo": 0}
        evolucao = {}
        recentes = []

        for item in concluidos:
            resultado = {}
            if item.resultado_groq:
                try:
                    resultado = json.loads(item.resultado_groq.replace("'", '"'))
                except Exception:
                    try:
                        import ast
                        resultado = ast.literal_eval(item.resultado_groq)
                    except Exception:
                        resultado = {}

            qualidade   = resultado.get("qualidade", {})
            classif     = resultado.get("classificacao", {})
            score       = qualidade.get("score_final", 0) or 0
            sentimento  = classif.get("sentimento", "Neutro")
            resumo      = resultado.get("resumo", "")
            categoria   = classif.get("categoria", "Geral")
            empatia     = qualidade.get("empatia", 0) or 0
            clareza     = qualidade.get("clareza", 0) or 0
            resolutiv   = qualidade.get("resolutividade", 0) or 0

            scores.append(float(score))

            # Sentimento
            s = sentimento.lower()
            if "positiv" in s:
                sentimentos["Positivo"] += 1
            elif "negativ" in s:
                sentimentos["Negativo"] += 1
            else:
                sentimentos["Neutro"] += 1

            # Evolução por dia
            if item.processado_em:
                dia = item.processado_em.strftime("%Y-%m-%d")
                if dia not in evolucao:
                    evolucao[dia] = {"scores": [], "empatia": [], "clareza": [], "resolutividade": []}
                evolucao[dia]["scores"].append(float(score))
                evolucao[dia]["empatia"].append(float(empatia))
                evolucao[dia]["clareza"].append(float(clareza))
                evolucao[dia]["resolutividade"].append(float(resolutiv))

            # Recentes
            recentes.append({
                "id":         item.id,
                "category":   categoria,
                "sentiment":  "positive" if "positiv" in sentimento.lower() else ("negative" if "negativ" in sentimento.lower() else "neutral"),
                "score":      float(score),
                "summary":    resumo,
                "created_at": item.criado_em.isoformat() if item.criado_em else "",
                "empathy":    float(empatia),
                "clarity":    float(clareza),
                "objectivity":  float(qualidade.get("objetividade", 0) or 0),
                "resolutiveness": float(resolutiv),
                "sla_time_minutes": 0,
                "numero_protocolo": item.numero_protocolo,
                "cliente_nome":     item.cliente_nome,
                "atendente_nome":   item.atendente_nome,
            })

        media_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        # Evolução formatada
        evolucao_lista = sorted([
            {
                "date":           dia,
                "media_score":    round(sum(v["scores"]) / len(v["scores"]), 2),
                "empathy":        round(sum(v["empatia"]) / len(v["empatia"]), 2),
                "clarity":        round(sum(v["clareza"]) / len(v["clareza"]), 2),
                "resolutiveness": round(sum(v["resolutividade"]) / len(v["resolutividade"]), 2),
                "objectivity":    0,
            }
            for dia, v in evolucao.items()
        ], key=lambda x: x["date"])

        # Distribução de sentimento
        dist_sentimento = [
            {"sentimento": "Positivo", "total": sentimentos["Positivo"]},
            {"sentimento": "Neutro",   "total": sentimentos["Neutro"]},
            {"sentimento": "Negativo", "total": sentimentos["Negativo"]},
        ]

        return jsonify({
            "sucesso": True,
            "dados": {
                "total_atendimentos":      total,
                "media_score_final":       media_score,
                "distribuicao_sentimento": dist_sentimento,
                "evolucao_score_diaria":   evolucao_lista,
                "recentes":                list(reversed(recentes))[:10],
            },
        }), 200

    except Exception as exc:
        logger.exception("Erro ao gerar resumo.")
        return jsonify({"sucesso": False, "erro": str(exc)}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/qualidade
# ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/qualidade", methods=["GET"])
def media_qualidade():
    try:
        row = db.session.query(
            func.round(func.avg(Qualidade.empatia),        2).label("empatia"),
            func.round(func.avg(Qualidade.clareza),        2).label("clareza"),
            func.round(func.avg(Qualidade.objetividade),   2).label("objetividade"),
            func.round(func.avg(Qualidade.resolutividade), 2).label("resolutividade"),
        ).first()
        return jsonify({"sucesso": True, "dados": {
            "empatia":        float(row.empatia)        if row.empatia        else 0.0,
            "clareza":        float(row.clareza)        if row.clareza        else 0.0,
            "objetividade":   float(row.objetividade)   if row.objetividade   else 0.0,
            "resolutividade": float(row.resolutividade) if row.resolutividade else 0.0,
        }}), 200
    except Exception as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), 500