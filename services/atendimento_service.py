"""
services/atendimento_service.py — Orquestra o fluxo completo:
  1. Chama o Groq para analisar a conversa.
  2. Mapeia o resultado para os modelos do banco.
  3. Persiste tudo em uma única transação.
  4. Salva também na avaliacao_fila para aparecer no dashboard.
"""

import json
import logging
from decimal import Decimal
from datetime import datetime

from config import db
from models import (
    Atendimento,
    AvaliacaoFila,
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


def _get_or_create(model, filter_kwargs: dict, extra_kwargs: dict | None = None):
    instance = model.query.filter_by(**filter_kwargs).first()
    if instance is None:
        kwargs = {**filter_kwargs, **(extra_kwargs or {})}
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.flush()
        logger.debug("Criado novo registro %s: %s", model.__tablename__, kwargs)
    return instance


def processar_atendimento(texto_conversa: str, numero_protocolo: str | None = None) -> dict:
    # ── 1. Analisar com o LLM
    analise = analisar_atendimento(texto_conversa)

    # ── 2. Extrair sub-objetos
    classif_data     = analise.get("classificacao", {})
    qualidade_data   = analise.get("qualidade", {})
    topicos_nomes    = analise.get("topicos", [])
    resumo           = analise.get("resumo", "")
    criticidade_data = classif_data.get("criticidade", {})

    try:
        # ── 3. Lookup tables
        categoria = _get_or_create(Categoria,   {"nome": classif_data.get("categoria",  "Não classificado")})
        intencao  = _get_or_create(Intencao,    {"nome": classif_data.get("intencao",   "Não identificada")})
        sentimento = _get_or_create(Sentimento, {"nome": classif_data.get("sentimento", "Neutro")})
        criticidade = _get_or_create(
            Criticidade,
            {"nome": criticidade_data.get("nome", "Baixa")},
            {"nivel": int(criticidade_data.get("nivel", 1))},
        )
        sla = _get_or_create(Sla, {"prazo": classif_data.get("sla", "24 horas")})

        # ── 4. Tópicos
        topicos_objs = []
        for nome_topico in topicos_nomes:
            nome_topico = nome_topico.strip()
            if nome_topico:
                topicos_objs.append(_get_or_create(Topico, {"nome": nome_topico}))

        # ── 5. Atendimento principal
        atendimento = Atendimento(texto=texto_conversa, resumo=resumo)
        atendimento.topicos = topicos_objs
        db.session.add(atendimento)
        db.session.flush()

        # ── 6. Classificação
        classificacao = Classificacao(
            atendimento_id=atendimento.idatendimento,
            categoria_id=categoria.idcategoria,
            intencao_id=intencao.idintencao,
            sentimento_id=sentimento.idsentimento,
            criticidade_id=criticidade.idcriticidade,
            sla_id=sla.idsla,
        )
        db.session.add(classificacao)

        # ── 7. Qualidade
        empatia        = int(qualidade_data.get("empatia",        0))
        clareza        = int(qualidade_data.get("clareza",        0))
        objetividade   = int(qualidade_data.get("objetividade",   0))
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

        # ── 8. Salva na avaliacao_fila para aparecer no dashboard
        if not numero_protocolo:
            numero_protocolo = f"MANUAL-{atendimento.idatendimento}"

        # Converte o texto em lista de mensagens
        mensagens = []
        for linha in texto_conversa.split("\n"):
            linha = linha.strip()
            if not linha:
                continue
            if ":" in linha:
                partes = linha.split(":", 1)
                mensagens.append({
                    "remetente": partes[0].strip(),
                    "conteudo":  partes[1].strip(),
                    "enviadaEm": datetime.utcnow().isoformat(),
                })
            else:
                mensagens.append({
                    "remetente": "Desconhecido",
                    "conteudo":  linha,
                    "enviadaEm": datetime.utcnow().isoformat(),
                })

        fila = AvaliacaoFila(
            protocol_id      = atendimento.idatendimento,
            numero_protocolo = numero_protocolo,
            cliente_nome     = "Análise Manual",
            atendente_nome   = "Análise Manual",
            mensagens        = mensagens,
            status           = "concluido",
            resultado_groq   = json.dumps(analise, ensure_ascii=False),
            processado_em    = datetime.utcnow(),
            tentativas       = 1,
        )
        db.session.add(fila)

        # ── 9. Commit único
        db.session.commit()
        logger.info("Atendimento #%d salvo com sucesso.", atendimento.idatendimento)

        return {
            "atendimento_id": atendimento.idatendimento,
            "score_final":    float(score_final),
        }

    except Exception as exc:
        db.session.rollback()
        logger.error("Rollback. Erro: %s", exc)
        raise