from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from database import Base, engine, SessionLocal, load_users_backup, save_user_to_backup
from models.user import User
from models.prediction import Prediction
from utils.security import hash_password
from routes.auth import router as auth_router
from routes.heart import router as heart_router
from routes.liver import router as liver_router
from routes.pcos import router as pcos_router
from routes.pcod import router as pcod_router
from routes import stroke
from routes import kidney
from routes import emergency
from routes import predictions

# Ensure database tables are created and rehydrate users from persistent backup
def init_db_and_seed():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            # Rehydrate cached users into database
            backup_users = load_users_backup()
            for email, data in backup_users.items():
                clean_email = email.lower().strip()
                existing = db.query(User).filter(User.email == clean_email).first()
                if not existing and data.get("password"):
                    u = User(
                        full_name=data.get("full_name", clean_email.split("@")[0]),
                        email=clean_email,
                        password=data.get("password"),
                        gender=data.get("gender"),
                        age=data.get("age"),
                        phone=data.get("phone")
                    )
                    db.add(u)

            # Ensure default demo user exists for seamless evaluation
            demo_email = "demo@quantummed.ai"
            if not db.query(User).filter(User.email == demo_email).first():
                demo_hash = hash_password("password123")
                demo_user = User(
                    full_name="Quantum Medical Demo",
                    email=demo_email,
                    password=demo_hash,
                    gender="Female",
                    age=28,
                    phone="9876543210"
                )
                db.add(demo_user)
                save_user_to_backup("Quantum Medical Demo", demo_email, demo_hash, "Female", 28, "9876543210")

            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")

init_db_and_seed()

app = FastAPI(
    title="QuantumMedAI API",
    description="Hybrid Quantum Deep Learning Framework for Multi-Disease Prediction and Intelligent Emergency Response Support",
    version="1.0.0"
)

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Register All API Routers
app.include_router(auth_router)
app.include_router(heart_router)
app.include_router(liver_router)
app.include_router(pcos_router)
app.include_router(pcod_router)
app.include_router(stroke.router)
app.include_router(kidney.router)
app.include_router(emergency.router)
app.include_router(predictions.router)


@app.get("/")
def home():
    return {
        "project": "QuantumMedAI",
        "message": "Welcome to QuantumMedAI Backend 🚀",
        "status": "Backend is running successfully!",
        "endpoints": {
            "auth": ["/auth/register", "/auth/login", "/auth/me"],
            "predictions": [
                "/heart/predict",
                "/liver/predict",
                "/kidney/predict",
                "/stroke/predict",
                "/pcos/predict",
                "/pcod/predict",
                "/emergency/check",
                "/predictions/symptoms",
                "/predictions/history"
            ],
            "docs": "/docs"
        }
    }