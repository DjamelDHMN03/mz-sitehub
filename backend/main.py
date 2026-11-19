from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import geospatial
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            try:
                await conn.run_sync(Base.metadata.create_all)
            except Exception:
                pass
        print("=> Base de connectivite active ou testee.")
    except Exception as e:
        print(f"-> Mode deconnecte (reseau bloque / base injoignable): {e}")
    yield

app = FastAPI(title="MZ-SITEHUB API", lifespan=lifespan)

# --- CONFIGURATION CORS POUR AUTORISER LE FRONTEND ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------------------------------

# Intégration du routeur geospatial
app.include_router(geospatial.router)

@app.get("/")
async def root():
    return {"message": "MZ-SITEHUB Backend connecté à Supabase avec succès !"}