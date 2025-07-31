import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Exporta a aplicação FastAPI para o Vercel
handler = app 