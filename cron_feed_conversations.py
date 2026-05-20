"""
cron_feed_conversations.py — Cron job para consumir conversas de um sistema externo
e enviar cada item para o endpoint local de avaliação `/api/atendimento/avaliar`.
"""

import logging
import os
from dotenv import load_dotenv
import requests

from config import create_app
from services.external_feed_service import buscar_conversas_externas
from services.atendimento_service import processar_atendimento

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEFAULT_LOCAL_API_URL = "http://localhost:5000/api/atendimento/avaliar"
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3


def _get_env_var(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def _build_local_headers() -> dict:
    token = os.getenv("LOCAL_API_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _format_external_id(item: dict, index: int) -> str:
    if item.get("external_id"):
        return str(item["external_id"]).strip()
    if item.get("id") is not None:
        return str(item["id"]).strip()
    if item.get("conversation_id") is not None:
        return str(item["conversation_id"]).strip()
    return f"external-{index}"


def _build_texto_conversa(item: dict) -> str | None:
    for key in ("texto_conversa", "texto", "mensagem", "descricao", "conversation_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _post_to_local_api(payload: dict) -> requests.Response | None:
    local_url = _get_env_var("LOCAL_API_URL", DEFAULT_LOCAL_API_URL)
    timeout = int(_get_env_var("LOCAL_API_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT)) or DEFAULT_REQUEST_TIMEOUT)
    retries = int(_get_env_var("LOCAL_API_RETRY", str(DEFAULT_MAX_RETRIES)) or DEFAULT_MAX_RETRIES)
    headers = _build_local_headers()

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(local_url, json=payload, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            logging.warning(
                "Tentativa %d/%d falhou ao enviar conversa %s ao endpoint local: %s",
                attempt,
                retries,
                payload.get("external_id"),
                exc,
            )
    return None


def feed_conversations():
    logging.info("Iniciando sincronização de conversas externas...")

    conversas = buscar_conversas_externas()
    if not conversas:
        logging.info("Nenhuma conversa pendente encontrada na API externa.")
        return

    local_url = _get_env_var("LOCAL_API_URL", DEFAULT_LOCAL_API_URL)
    api_available = bool(local_url)

    for idx, item in enumerate(conversas, start=1):
        external_id = _format_external_id(item, idx)
        texto_conversa = _build_texto_conversa(item)

        if not texto_conversa:
            logging.warning("Conversa externa %s ignorada: texto não encontrado.", external_id)
            continue

        payload = {
            "texto_conversa": texto_conversa,
            "external_id": external_id,
        }

        if api_available:
            response = _post_to_local_api(payload)
            if response is not None:
                logging.info(
                    "Conversa externa %s processada via endpoint local com status %d.",
                    external_id,
                    response.status_code,
                )
                continue
            logging.warning(
                "Falha ao enviar conversa %s para o endpoint local. Habilitando fallback interno.",
                external_id,
            )

        try:
            app = create_app()
            with app.app_context():
                resultado = processar_atendimento(texto_conversa, external_id=external_id)
                logging.info(
                    "Conversa externa %s processada internamente como atendimento %d.",
                    external_id,
                    resultado["atendimento_id"],
                )
        except Exception as exc:
            logging.error(
                "Erro ao processar conversa externa %s internamente: %s",
                external_id,
                exc,
            )

    logging.info("Sincronização de conversas externas finalizada.")


if __name__ == "__main__":
    feed_conversations()
