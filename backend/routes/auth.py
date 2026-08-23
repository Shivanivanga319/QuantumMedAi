from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.jwt_handler import verify_token, create_access_token

from database import SessionLocal
from models.user import User
from schemas.user_schema import UserRegister, UserLogin
from utils.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    new_user = User(
        full_name=user.full_name,
        email=user.email.lower().strip(),
        password=hash_password(user.password),
        gender=user.gender,
        age=user.age,
        phone=user.phone
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.full_name
        }
    )

    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "token_type": "Bearer",
        "user": {
            "id": new_user.id,
            "name": new_user.full_name,
            "email": new_user.email,
            "gender": new_user.gender,
            "age": new_user.age,
            "phone": new_user.phone
        }
    }



@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Email address"
        )

    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Password"
        )

    access_token = create_access_token(
        {
            "id": user.id,
            "email": user.email,
            "name": user.full_name
        }
    )

    return {
        "message": "Login Successful",
        "access_token": access_token,
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "gender": user.gender,
            "age": user.age,
            "phone": user.phone
        }
    }


@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token"
        )

    return {
        "message": "Token Verified Successfully",
        "user": payload
    }