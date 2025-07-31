from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Configurações da Aplicação
    app_name: str = "Chatbot Clínica Gabriela Nassif"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Z-API Configuration
    zapi_instance_id: str = "3E4F7360B552F0C2DBCB9E6774402775"
    zapi_token: str = "17829E98BB59E9ADD55BBBA9"
    zapi_client_token: str = "F909fc109aad54566bf42a6d09f00a8dbS"
    zapi_base_url: str = "https://api.z-api.io"
    
    # Supabase Configuration
    supabase_url: str = "https://feqylqrphdpeeusdyeyw.supabase.co"
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    
    # GestãoDS Configuration
    gestaods_api_url: str = "https://apidev.gestaods.com.br"
    gestaods_token: str = "733a8e19a94b65d58390da380ac946b6d603a535"
    
    # Clínica Configuration
    clinic_name: str = "Clínica Gabriela Nassif"
    clinic_phone: str = "+553198600366"
    clinic_address: str = "Endereço da Clínica"
    
    # Performance Configuration
    max_message_length: int = 1000
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    request_timeout: int = 10
    
    # Cache Configuration
    cache_ttl_patient: int = 300  # 5 minutos
    cache_ttl_schedule: int = 120  # 2 minutos
    cache_ttl_conversation: int = 1800  # 30 minutos
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Singleton instance
_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 