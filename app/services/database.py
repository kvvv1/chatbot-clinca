from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
from app.config import get_settings
from app.models.database import Base
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()

# Cliente Supabase
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

# Engine SQLAlchemy para Supabase
if settings.database_url:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20
    )
else:
    # Fallback para SQLite em desenvolvimento
    engine = create_async_engine(
        "sqlite+aiosqlite:///./chatbot.db",
        echo=settings.debug
    )

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency para obter sessão do banco"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()

async def init_db():
    """Inicializa as tabelas no banco"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

async def check_db_connection() -> bool:
    """Verifica se a conexão com o banco está funcionando"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False

# Funções auxiliares para Supabase
async def get_patient_from_supabase(cpf: str) -> dict:
    """Busca paciente no Supabase"""
    try:
        response = supabase.table("patients").select("*").eq("cpf", cpf).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Failed to get patient from Supabase", cpf=cpf, error=str(e))
        return None

async def save_appointment_to_supabase(appointment_data: dict) -> dict:
    """Salva agendamento no Supabase"""
    try:
        response = supabase.table("appointments").insert(appointment_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Failed to save appointment to Supabase", error=str(e))
        return None

async def get_appointments_from_supabase(patient_cpf: str) -> list:
    """Busca agendamentos do paciente no Supabase"""
    try:
        response = supabase.table("appointments").select("*").eq("patient_cpf", patient_cpf).execute()
        return response.data or []
    except Exception as e:
        logger.error("Failed to get appointments from Supabase", cpf=patient_cpf, error=str(e))
        return [] 