from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.jwt_handler import verify_token, create_access_token

from database import SessionLocal, save_user_to_backup, get_user_from_backup
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
    clean_email = user.email.lower().strip()
    
    # Case-insensitive email query
    existing_user = db.query(User).filter(func.lower(User.email) == clean_email).first()

    if existing_user:
        # If user exists, update password and profile to keep in sync
        existing_user.full_name = user.full_name.strip()
        existing_user.password = hash_password(user.password)
        if user.gender:
            existing_user.gender = user.gender
        if user.age:
            existing_user.age = user.age
        if user.phone:
            existing_user.phone = user.phone
        
        db.commit()
        db.refresh(existing_user)
        target_user = existing_user
    else:
        hashed_pwd = hash_password(user.password)
        new_user = User(
            full_name=user.full_name.strip(),
            email=clean_email,
            password=hashed_pwd,
            gender=user.gender,
            age=user.age,
            phone=user.phone
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        target_user = new_user

    # Persist to local JSON backup to survive Render container redeployments
    save_user_to_backup(
        full_name=target_user.full_name,
        email=clean_email,
        password_hash=target_user.password,
        gender=target_user.gender,
        age=target_user.age,
        phone=target_user.phone
    )

    access_token = create_access_token(
        {
            "id": target_user.id,
            "email": target_user.email,
            "name": target_user.full_name
        }
    )

    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "token_type": "Bearer",
        "user": {
            "id": target_user.id,
            "name": target_user.full_name,
            "email": target_user.email,
            "gender": target_user.gender,
            "age": target_user.age,
            "phone": target_user.phone
        }
    }



@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    clean_email = credentials.email.lower().strip()
    
    # 1. Search in Database (case-insensitive)
    user = db.query(User).filter(func.lower(User.email) == clean_email).first()

    # 2. If not in active database, check persistent container backup (rehydration)
    if not user:
        backup = get_user_from_backup(clean_email)
        if backup and verify_password(credentials.password, backup["password"]):
            # Rehydrate into database table
            user = User(
                full_name=backup.get("full_name", clean_email.split('@')[0]),
                email=clean_email,
                password=backup["password"],
                gender=backup.get("gender"),
                age=backup.get("age"),
                phone=backup.get("phone")
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Email address. No account found with this email."
        )

    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Password. Please check your password and try again."
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