import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verificar_api_key(api_key: str = Security(api_key_header)) -> str:
    esperada = os.getenv("API_KEY", "flos-dev-key-2026")
    if api_key is None or api_key != esperada:
        raise HTTPException(status_code=401, detail="API Key invalida o no proporcionada")
    return api_key
