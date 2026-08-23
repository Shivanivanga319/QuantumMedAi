from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = "quantummedai_secret_key"
ALGORITHM = "HS256"
# Token valid for 90 days (3 months)
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 90



def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        return None