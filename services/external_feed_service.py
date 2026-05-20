import logging
import os
from dotenv import load_dotenv
import requests

load_dotenv(override=True)

logger = logging.getLogger(__name__)

DEFAULT_EXTERNAL_API_URL = "https://api-externa.com/api/conversas/pendentes"
DEFAULT_TIMEOUT = 30


def _get_env_var(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        logger.error("Variável de ambiente obrigatória não definida: %s", name)
    return value


def buscar_conversas_externas() -> list[dict]:
    url = _get_env_var("EXTERNAL_API_URL", DEFAULT_EXTERNAL_API_URL, required=True)
    timeout = int(_get_env_var("EXTERNAL_API_TIMEOUT", str(DEFAULT_TIMEOUT)) or DEFAULT_TIMEOUT)
    token = os.getenv("EXTERNAL_API_TOKEN")

    if not url or url == DEFAULT_EXTERNAL_API_URL:
        logger.error(
            "EXTERNAL_API_URL não está configurada corretamente. Atualize .env com a URL do endpoint externo."
        )
        return []

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        logger.info("Consultando endpoint externo de conversas pendentes: %s", url)
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        dados = response.json()
        if not isinstance(dados, list):
            logger.error("Resposta inválida da API externa: esperava lista, recebeu %s", type(dados).__name__)
            return []

        conversas = [item for item in dados if isinstance(item, dict)]
        logger.info("Foram encontradas %d conversas pendentes na API externa.", len(conversas))
        return conversas

    except requests.exceptions.Timeout:
        logger.error("Timeout ao consultar a API externa de conversas.")
        return []

    except requests.exceptions.RequestException as exc:
        logger.error("Erro ao consumir a API externa de conversas: %s", exc)
        return []

    except ValueError as exc:
        logger.error("Resposta JSON inválida da API externa: %s", exc)
        return []
