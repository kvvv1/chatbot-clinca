import httpx
import asyncio
import time
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.monitoring import metrics
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()

class WhatsAppServiceError(Exception):
    """Exceção base para erros do WhatsApp Service"""
    pass

class WhatsAppConnectionError(WhatsAppServiceError):
    """Erro de conexão com Z-API"""
    pass

class WhatsAppRateLimitError(WhatsAppServiceError):
    """Rate limit excedido"""
    pass

class WhatsAppService:
    def __init__(self):
        self.base_url = f"{settings.zapi_base_url}/instances/{settings.zapi_instance_id}/token/{settings.zapi_token}"
        self.headers = {
            "Client-Token": settings.zapi_client_token,
            "Content-Type": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        
        # Cliente HTTP otimizado
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=10.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30
            ),
            headers=self.headers,
            follow_redirects=True
        )
        
        # Circuit Breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
            name="whatsapp_service"
        )
        
        # Rate Limiter (30 req/min para Z-API)
        self.rate_limiter = asyncio.Semaphore(30)
        self.last_requests = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _check_rate_limit(self):
        """Controla rate limit de 30 req/min"""
        now = time.time()
        # Remove requests mais antigos que 1 minuto
        self.last_requests = [req_time for req_time in self.last_requests if now - req_time < 60]
        
        if len(self.last_requests) >= 30:
            sleep_time = 60 - (now - self.last_requests[0])
            if sleep_time > 0:
                logger.warning("Rate limit approaching, sleeping", sleep_time=sleep_time)
                await asyncio.sleep(sleep_time)
        
        self.last_requests.append(now)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, WhatsAppConnectionError)),
        reraise=True
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Faz requisição HTTP com retry e circuit breaker"""
        await self._check_rate_limit()
        
        async with self.rate_limiter:
            try:
                async with self.circuit_breaker:
                    url = f"{self.base_url}/{endpoint}"
                    
                    logger.debug("Making WhatsApp API request", 
                                method=method, endpoint=endpoint, url=url)
                    
                    response = await self.client.request(method, url, **kwargs)
                    
                    # Log da resposta
                    logger.debug("WhatsApp API response", 
                                status_code=response.status_code,
                                response_size=len(response.content))
                    
                    # Tratamento de erros HTTP
                    if response.status_code == 401:
                        logger.error("Z-API authentication failed", 
                                   instance_id=settings.zapi_instance_id)
                        metrics.increment("whatsapp_auth_errors")
                        raise WhatsAppConnectionError("Authentication failed - check Z-API credentials")
                    
                    elif response.status_code == 429:
                        logger.warning("Z-API rate limit exceeded")
                        metrics.increment("whatsapp_rate_limit_errors")
                        raise WhatsAppRateLimitError("Rate limit exceeded")
                    
                    elif response.status_code == 404:
                        logger.error("Z-API instance not found", 
                                   instance_id=settings.zapi_instance_id)
                        raise WhatsAppConnectionError("Instance not found - check Z-API instance ID")
                    
                    elif response.status_code >= 500:
                        logger.error("Z-API server error", 
                                   status_code=response.status_code,
                                   response_text=response.text)
                        metrics.increment("whatsapp_server_errors")
                        raise WhatsAppConnectionError(f"Z-API server error: {response.status_code}")
                    
                    elif response.status_code >= 400:
                        logger.error("Z-API client error", 
                                   status_code=response.status_code,
                                   response_text=response.text)
                        metrics.increment("whatsapp_client_errors")
                        raise WhatsAppServiceError(f"Z-API client error: {response.status_code}")
                    
                    # Sucesso
                    metrics.increment("whatsapp_requests_success")
                    return response.json()
                    
            except httpx.TimeoutException as e:
                logger.error("Z-API request timeout", error=str(e))
                metrics.increment("whatsapp_timeout_errors")
                raise WhatsAppConnectionError(f"Request timeout: {e}")
            
            except httpx.ConnectError as e:
                logger.error("Z-API connection error", error=str(e))
                metrics.increment("whatsapp_connection_errors")
                raise WhatsAppConnectionError(f"Connection error: {e}")
            
            except Exception as e:
                logger.error("Unexpected WhatsApp API error", error=str(e))
                metrics.increment("whatsapp_unknown_errors")
                raise WhatsAppServiceError(f"Unexpected error: {e}")
    
    def _format_phone(self, phone: str) -> str:
        """Formata número brasileiro para Z-API"""
        # Remove tudo exceto números
        clean = ''.join(filter(str.isdigit, phone))
        
        # Validação básica
        if len(clean) < 10:
            raise ValueError(f"Invalid phone number: {phone}")
        
        # Adiciona código do país se necessário
        if len(clean) == 11:  # Celular brasileiro
            clean = '55' + clean
        elif len(clean) == 10:  # Fixo brasileiro
            clean = '55' + clean
        
        # Adiciona 9 no celular se não tiver
        if len(clean) == 12 and clean[4] != '9':
            clean = clean[:4] + '9' + clean[4:]
        
        # Formato final para Z-API
        formatted = clean + '@c.us'
        
        logger.debug("Phone formatted", original=phone, formatted=formatted)
        return formatted
    
    def _validate_message(self, message: str) -> str:
        """Valida e sanitiza mensagem"""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        
        # Limita tamanho da mensagem
        if len(message) > settings.max_message_length:
            logger.warning("Message truncated", 
                          original_length=len(message),
                          max_length=settings.max_message_length)
            message = message[:settings.max_message_length-3] + "..."
        
        return message.strip()
    
    async def send_text(self, phone: str, message: str, delay_message: int = 0) -> Optional[Dict]:
        """Envia mensagem de texto"""
        try:
            formatted_phone = self._format_phone(phone)
            validated_message = self._validate_message(message)
            
            payload = {
                "phone": formatted_phone,
                "message": validated_message,
                "delayMessage": delay_message
            }
            
            logger.info("Sending WhatsApp message", 
                       phone=formatted_phone,
                       message_length=len(validated_message),
                       delay=delay_message)
            
            result = await self._make_request("POST", "send-text", json=payload)
            
            logger.info("WhatsApp message sent successfully", 
                       phone=formatted_phone,
                       message_id=result.get('messageId'))
            
            metrics.increment("whatsapp_messages_sent")
            return result
            
        except Exception as e:
            logger.error("Failed to send WhatsApp message", 
                        phone=phone, error=str(e))
            metrics.increment("whatsapp_send_failures")
            return None
    
    async def mark_as_read(self, phone: str, message_id: str) -> bool:
        """Marca mensagem como lida"""
        try:
            formatted_phone = self._format_phone(phone)
            
            payload = {
                "phone": formatted_phone,
                "messageId": message_id
            }
            
            await self._make_request("POST", "read-message", json=payload)
            
            logger.debug("Message marked as read", 
                        phone=formatted_phone, message_id=message_id)
            
            metrics.increment("whatsapp_messages_read")
            return True
            
        except Exception as e:
            logger.error("Failed to mark message as read", 
                        phone=phone, message_id=message_id, error=str(e))
            return False
    
    async def check_connection(self) -> bool:
        """Verifica se a instância Z-API está conectada"""
        try:
            result = await self._make_request("GET", "status")
            connected = result.get('connected', False)
            
            logger.info("Z-API connection status", connected=connected)
            
            if connected:
                metrics.set("whatsapp_connection_status", 1)
            else:
                metrics.set("whatsapp_connection_status", 0)
            
            return connected
            
        except Exception as e:
            logger.error("Failed to check Z-API connection", error=str(e))
            metrics.set("whatsapp_connection_status", 0)
            return False
    
    async def send_typing_indicator(self, phone: str) -> bool:
        """Envia indicador de digitação"""
        try:
            formatted_phone = self._format_phone(phone)
            
            # Z-API não tem endpoint específico para typing
            # Usamos um delay na próxima mensagem como alternativa
            logger.debug("Typing indicator requested", phone=formatted_phone)
            return True
            
        except Exception as e:
            logger.error("Failed to send typing indicator", phone=phone, error=str(e))
            return False

# Singleton instance
_whatsapp_service = None

async def get_whatsapp_service() -> WhatsAppService:
    """Retorna instância singleton do WhatsApp service"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service 