import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET", "flos-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

ROLES = ("admin", "ingenieria", "almacen", "produccion", "consultor")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def crear_token(username: str, rol: str, nombre: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "rol": rol, "nombre": nombre, "exp": exp},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _decodificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Se requiere autenticacion")
    return _decodificar_token(credenciales.credentials)


def requerir_rol(*roles: str):
    async def _dependency(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
        if usuario.get("rol") not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta accion")
        return usuario

    return _dependency
