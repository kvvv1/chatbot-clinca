import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

try:
    from app.main import app
    handler = app
except ImportError as e:
    print(f"Erro ao importar app: {e}")
    # Fallback básico
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "Chatbot Clínica - Deploy em andamento"}
    
    @app.get("/health")
    async def health():
        return {"status": "degraded", "message": "Deploy em configuração"}
    
    handler = app 