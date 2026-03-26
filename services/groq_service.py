"""
services/groq_service.py — Integração com a API do Groq.

Envia a transcrição de um atendimento ao LLM e retorna um JSON
estruturado com métricas de qualidade e classificações.
"""

import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Cliente Groq (singleton)
# ──────────────────────────────────────────────────────────────
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY não está definida nas variáveis de ambiente.")
        _client = Groq(api_key=api_key)
    return _client


# ──────────────────────────────────────────────────────────────
# Prompt de sistema — Schema rígido exigido ao LLM
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Você é um especialista em análise de qualidade de atendimento ao cliente.
Sua única função é ler a transcrição de um atendimento e retornar
EXCLUSIVAMENTE um objeto JSON válido, sem nenhum texto antes ou depois.

O JSON deve seguir ESTRITAMENTE este schema:

{
  "resumo": "<string: resumo objetivo da conversa em até 3 frases>",

  "classificacao": {
    "categoria":   "<string: ex.: Suporte Técnico, Comercial, Financeiro, Reclamação, Elogio, Informação>",
    "intencao":    "<string: ex.: Cancelamento, Ativação, Reclamação, Consulta, Troca, Reembolso>",
    "sentimento":  "<string: APENAS UM DE: Positivo | Negativo | Neutro | Misto>",
    "criticidade": {
      "nome":  "<string: APENAS UM DE: Baixa | Média | Alta | Crítica>",
      "nivel": "<integer: Baixa=1, Média=2, Alta=3, Crítica=4>"
    },
    "sla": "<string: prazo sugerido, ex.: 4 horas | 24 horas | 48 horas | 72 horas>"
  },

  "topicos": ["<string>", "<string>"],

  "qualidade": {
    "empatia":        <integer 0-10>,
    "clareza":        <integer 0-10>,
    "objetividade":   <integer 0-10>,
    "resolutividade": <integer 0-10>,
    "score_final":    <float: média dos 4 campos acima, com 2 casas decimais>
  }
}

Regras obrigatórias:
1. Retorne SOMENTE o JSON. Sem markdown, sem explicações, sem blocos de código.
2. Todos os campos são obrigatórios.
3. "topicos" deve ter entre 1 e 5 itens relevantes sobre o atendimento.
4. "score_final" deve ser exatamente a média aritmética dos 4 campos de qualidade.
5. Valores de qualidade devem ser inteiros entre 0 e 10.
"""


# ──────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────
def analisar_atendimento(texto_conversa: str) -> dict:
    """
    Envia o texto ao Groq e retorna o dicionário Python com a análise.

    Args:
        texto_conversa: Transcrição bruta do atendimento ao cliente.

    Returns:
        dict: Resposta estruturada do LLM já parseada.

    Raises:
        ValueError: Se o LLM não retornar JSON válido.
        RuntimeError: Em caso de falha na chamada à API do Groq.
    """
    client = _get_client()

    try:
        logger.info("Enviando atendimento para análise no Groq...")

        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Analise o atendimento abaixo e retorne o JSON conforme instruído:\n\n"
                        f"{texto_conversa}"
                    ),
                },
            ],
            temperature=0.1,          # baixa temperatura → maior consistência
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw_content = chat_completion.choices[0].message.content
        logger.debug("Resposta bruta do Groq: %s", raw_content)

        resultado = json.loads(raw_content)
        logger.info("Análise concluída com sucesso.")
        return resultado

    except json.JSONDecodeError as exc:
        logger.error("Falha ao parsear JSON do Groq: %s", exc)
        raise ValueError(f"O LLM não retornou um JSON válido: {exc}") from exc

    except Exception as exc:
        logger.error("Erro na chamada à API do Groq: %s", exc)
        raise RuntimeError(f"Erro ao comunicar com a API do Groq: {exc}") from exc
