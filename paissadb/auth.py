from typing import Optional

import jwt
from fastapi import HTTPException, Header

from . import schemas, config


def maybe(authorization: Optional[str] = Header(None)) -> Optional[schemas.paissa.JWTSweeper]:
    if authorization is None:
        return None
    return required(authorization)


def required(authorization: str = Header(None)) -> schemas.paissa.JWTSweeper:
    if authorization is None:
        raise HTTPException(401)
    token = authorization.removeprefix("Bearer ")
    try:
        claim = jwt.decode(token, key=config.JWT_SECRET_PAISSAHOUSE, algorithms=['HS256'],
                           options={'verify_aud': True, 'verify_iss': True},
                           audience=config.JWT_AUDIENCES, issuer=config.JWT_ISSUER)
    except jwt.InvalidTokenError as e:
        raise HTTPException(400, str(e))
    return schemas.paissa.JWTSweeper(**claim)
