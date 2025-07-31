from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import time
from datetime import datetime

from app.config import get_settings
from app.services.whatsapp import get_whatsapp_service
from app.services.gestaods import get_gestaods_service
from app.services.database import check_db_connection, init_db
from app.handlers.webhook import router as webhook_router
from app.utils.monitoring import metrics
import structlog

# Configuração de logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
settings = get_settings()

# Criação da aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Chatbot WhatsApp para Clínica Gabriela Nassif",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos routers
app.include_router(webhook_router, prefix="/api/v1", tags=["webhooks"])

@app.on_event("startup")
async def startup_event():
    """Evento executado na inicialização da aplicação"""
    logger.info("Starting up chatbot application", 
               app_name=settings.app_name,
               version=settings.app_version)
    
    try:
        # Inicializa banco de dados
        await init_db()
        logger.info("Database initialized successfully")
        
        # Verifica conexões
        await check_connections()
        
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Evento executado no shutdown da aplicação"""
    logger.info("Shutting down chatbot application")

async def check_connections():
    """Verifica todas as conexões externas"""
    try:
        # Verifica WhatsApp
        whatsapp_service = await get_whatsapp_service()
        whatsapp_connected = await whatsapp_service.check_connection()
        logger.info("WhatsApp connection check", connected=whatsapp_connected)
        
        # Verifica GestãoDS
        gestaods_service = await get_gestaods_service()
        gestaods_connected = await gestaods_service.check_connection()
        logger.info("GestãoDS connection check", connected=gestaods_connected)
        
        # Verifica banco de dados
        db_connected = await check_db_connection()
        logger.info("Database connection check", connected=db_connected)
        
    except Exception as e:
        logger.error("Connection check failed", error=str(e))

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check completo da aplicação"""
    start_time = time.time()
    
    try:
        # Verifica todas as conexões em paralelo
        checks = await asyncio.gather(
            check_whatsapp_health(),
            check_gestaods_health(),
            check_database_health(),
            return_exceptions=True
        )
        
        # Processa resultados
        whatsapp_ok = isinstance(checks[0], bool) and checks[0]
        gestaods_ok = isinstance(checks[1], bool) and checks[1]
        database_ok = isinstance(checks[2], bool) and checks[2]
        
        # Determina status geral
        all_healthy = whatsapp_ok and gestaods_ok and database_ok
        status = "healthy" if all_healthy else "degraded"
        
        response_time = time.time() - start_time
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time": response_time,
            "services": {
                "whatsapp": {
                    "status": "healthy" if whatsapp_ok else "unhealthy",
                    "connected": whatsapp_ok
                },
                "gestaods": {
                    "status": "healthy" if gestaods_ok else "unhealthy", 
                    "connected": gestaods_ok
                },
                "database": {
                    "status": "healthy" if database_ok else "unhealthy",
                    "connected": database_ok
                }
            },
            "uptime": metrics.get_uptime()
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

async def check_whatsapp_health() -> bool:
    """Verifica saúde do WhatsApp"""
    try:
        whatsapp_service = await get_whatsapp_service()
        return await whatsapp_service.check_connection()
    except Exception as e:
        logger.error("WhatsApp health check failed", error=str(e))
        return False

async def check_gestaods_health() -> bool:
    """Verifica saúde do GestãoDS"""
    try:
        gestaods_service = await get_gestaods_service()
        return await gestaods_service.check_connection()
    except Exception as e:
        logger.error("GestãoDS health check failed", error=str(e))
        return False

async def check_database_health() -> bool:
    """Verifica saúde do banco de dados"""
    try:
        return await check_db_connection()
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False

@app.get("/metrics")
async def get_metrics():
    """Endpoint para métricas da aplicação"""
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics.get_all_metrics()
        }
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@app.get("/dashboard")
async def dashboard():
    """Dashboard básico da aplicação"""
    try:
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "uptime": metrics.get_uptime(),
            "messages_today": metrics.get_counter("webhook_messages_received"),
            "responses_sent": metrics.get_counter("webhook_responses_sent"),
            "error_rate": metrics.get_counter("webhook_processing_errors"),
            "avg_response_time": metrics.get_histogram_stats("conversation_response_time", {}).get("mean", 0),
            "whatsapp_status": "connected" if metrics.get_gauge("whatsapp_connection_status") else "disconnected",
            "gestaods_status": "connected" if metrics.get_gauge("gestaods_connection_status") else "disconnected"
        }
    except Exception as e:
        logger.error("Failed to get dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard")

@app.post("/admin/send-message")
async def send_test_message(phone: str, message: str):
    """Endpoint administrativo para enviar mensagem de teste"""
    try:
        whatsapp_service = await get_whatsapp_service()
        result = await whatsapp_service.send_text(phone, message)
        
        if result:
            return {"status": "success", "message_id": result.get("messageId")}
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")
            
    except Exception as e:
        logger.error("Failed to send test message", phone=phone, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/reset-conversation/{phone}")
async def reset_conversation(phone: str):
    """Endpoint administrativo para resetar conversa"""
    try:
        from app.services.conversation import active_conversations
        
        if phone in active_conversations:
            del active_conversations[phone]
            logger.info("Conversation reset by admin", phone=phone)
            return {"status": "success", "message": "Conversation reset"}
        else:
            return {"status": "success", "message": "No conversation found"}
            
    except Exception as e:
        logger.error("Failed to reset conversation", phone=phone, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info("HTTP request processed",
               method=request.method,
               url=str(request.url),
               status_code=response.status_code,
               process_time=process_time)
    
    return response

# Handler de exceções globais
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception",
                method=request.method,
                url=str(request.url),
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    ) 