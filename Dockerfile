# Multi-stage build para otimização
FROM python:3.11-slim as builder

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage de produção
FROM python:3.11-slim

# Instala dependências mínimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN groupadd -r chatbot && useradd -r -g chatbot chatbot

# Cria diretório de trabalho
WORKDIR /app

# Copia dependências do stage anterior
COPY --from=builder /root/.local /home/chatbot/.local

# Copia código da aplicação
COPY app/ ./app/
COPY env.example .env

# Define PATH para incluir .local/bin
ENV PATH=/home/chatbot/.local/bin:$PATH

# Muda para usuário não-root
USER chatbot

# Expõe porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para executar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 