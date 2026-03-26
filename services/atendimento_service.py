"""
services/atendimento_service.py — Orquestra o fluxo completo:
  1. Chama o Groq para analisar a conversa.
  2. Mapeia o resultado para os modelos do banco.
  3. Persiste tudo em uma única transação.
"""

import logging
from decimal import Decimal

from config import db
from models import (
    Atendimento,
    Categoria,
    Classificacao,
    Criticidade,
    Intencao,
    Qualidade,
    Sentimento,
    Sla,
    Topico,
)
from services.groq_service import analisar_atendimento

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Helper: get_or_create
# ──────────────────────────────────────────────────────────────
def _get_or_create(model, filter_kwargs: dict, extra_kwargs: dict | None = None):
    """
    Retorna o primeiro registro que satisfaça filter_kwargs,
    ou cria um novo combinando filter_kwargs + extra_kwargs.
    """
    instance = model.query.filter_by(**filter_kwargs).first()
    if instance is None:
        kwargs = {**filter_kwargs, **(extra_kwargs or {})}
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.flush()  # garante que o id seja gerado antes do commit
        logger.debug("Criado novo registro %s: %s", model.__tablename__, kwargs)
    return instance


# ──────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────
def processar_atendimento(texto_conversa: str) -> dict:
    """
    Processa um atendimento de ponta a ponta.

    Args:
        texto_conversa: Texto bruto da conversa do cliente.

    Returns:
        dict com "atendimento_id" e "score_final".

    Raises:
        ValueError: Dados inválidos retornados pelo LLM.
        RuntimeError: Falhas na API do Groq.
        SQLAlchemyError: Falhas de persistência.
    """
    # ── 1. Analisar com o LLM ─────────────────────────────────
    analise = analisar_atendimento(texto_conversa)

    # ── 2. Extrair sub-objetos da resposta ────────────────────
    classif_data   = analise.get("classificacao", {})
    qualidade_data = analise.get("qualidade", {})
    topicos_nomes  = analise.get("topicos", [])
    resumo         = analise.get("resumo", "")

    criticidade_data = classif_data.get("criticidade", {})

    # ── 3. Persistir em transação ─────────────────────────────
    try:
        # 3a. Registros de domínio (lookup tables)
        categoria = _get_or_create(
            Categoria, {"nome": classif_data.get("categoria", "Não classificado")}
        )
        intencao = _get_or_create(
            Intencao, {"nome": classif_data.get("intencao", "Não identificada")}
        )
        sentimento = _get_or_create(
            Sentimento, {"nome": classif_data.get("sentimento", "Neutro")}
        )
        criticidade = _get_or_create(
            Criticidade,
            {"nome": criticidade_data.get("nome", "Baixa")},
            {"nivel": int(criticidade_data.get("nivel", 1))},
        )
        sla = _get_or_create(
            Sla, {"prazo": classif_data.get("sla", "24 horas")}
        )

        # 3b. Tópicos (N:N)
        topicos_objs = []
        for nome_topico in topicos_nomes:
            nome_topico = nome_topico.strip()
            if nome_topico:
                topico = _get_or_create(Topico, {"nome": nome_topico})
                topicos_objs.append(topico)

        # 3c. Atendimento principal
        atendimento = Atendimento(
            texto=texto_conversa,
            resumo=resumo,
        )
        atendimento.topicos = topicos_objs
        db.session.add(atendimento)
        db.session.flush()

        # 3d. Classificação
        classificacao = Classificacao(
            atendimento_id=atendimento.idatendimento,
            categoria_id=categoria.idcategoria,
            intencao_id=intencao.idintencao,
            sentimento_id=sentimento.idsentimento,
            criticidade_id=criticidade.idcriticidade,
            sla_id=sla.idsla,
        )
        db.session.add(classificacao)

        # 3e. Qualidade
        empatia        = int(qualidade_data.get("empatia", 0))
        clareza        = int(qualidade_data.get("clareza", 0))
        objetividade   = int(qualidade_data.get("objetividade", 0))
        resolutividade = int(qualidade_data.get("resolutividade", 0))
        score_final    = Decimal(str(qualidade_data.get(
            "score_final",
            round((empatia + clareza + objetividade + resolutividade) / 4, 2),
        )))

        qualidade = Qualidade(
            atendimento_id=atendimento.idatendimento,
            empatia=empatia,
            clareza=clareza,
            objetividade=objetividade,
            resolutividade=resolutividade,
            score_final=score_final,
        )
        db.session.add(qualidade)

        # 3f. Commit único
        db.session.commit()
        logger.info("Atendimento #%d salvo com sucesso.", atendimento.idatendimento)

        return {
            "atendimento_id": atendimento.idatendimento,
            "score_final": float(score_final),
        }

    except Exception as exc:
        db.session.rollback()
        logger.error("Rollback executado. Erro ao persistir atendimento: %s", exc)
        raise
