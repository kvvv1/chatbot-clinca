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

class GestaoDSError(Exception):
    """Exceção base para erros do GestãoDS"""
    pass

class GestaoDSConnectionError(GestaoDSError):
    """Erro de conexão com GestãoDS"""
    pass

class GestaoDSPatientNotFoundError(GestaoDSError):
    """Paciente não encontrado"""
    pass

class GestaoDSService:
    def __init__(self):
        self.base_url = settings.gestaods_api_url
        self.token = settings.gestaods_token
        
        # Cliente HTTP otimizado
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=10.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30
            ),
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"{settings.app_name}/{settings.app_version}"
            },
            follow_redirects=True
        )
        
        # Circuit Breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            name="gestaods_service"
        )
        
        # Cache simples em memória
        self._patient_cache = {}
        self._schedule_cache = {}
        self._cache_cleanup_task = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _cleanup_cache(self):
        """Remove entradas expiradas do cache"""
        now = time.time()
        
        # Limpa cache de pacientes (5 minutos)
        self._patient_cache = {
            k: v for k, v in self._patient_cache.items() 
            if now - v['timestamp'] < 300
        }
        
        # Limpa cache de horários (2 minutos)
        self._schedule_cache = {
            k: v for k, v in self._schedule_cache.items() 
            if now - v['timestamp'] < 120
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, GestaoDSConnectionError)),
        reraise=True
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Faz requisição HTTP com retry e circuit breaker"""
        try:
            async with self.circuit_breaker:
                url = f"{self.base_url}/{endpoint}"
                
                logger.debug("Making GestãoDS API request", 
                            method=method, endpoint=endpoint, url=url)
                
                response = await self.client.request(method, url, **kwargs)
                
                # Log da resposta
                logger.debug("GestãoDS API response", 
                            status_code=response.status_code,
                            response_size=len(response.content))
                
                # Tratamento de erros HTTP
                if response.status_code == 401:
                    logger.error("GestãoDS authentication failed")
                    metrics.increment("gestaods_auth_errors")
                    raise GestaoDSConnectionError("Authentication failed - check GestãoDS token")
                
                elif response.status_code == 404:
                    logger.warning("GestãoDS endpoint not found", endpoint=endpoint)
                    metrics.increment("gestaods_not_found_errors")
                    raise GestaoDSPatientNotFoundError("Resource not found")
                
                elif response.status_code >= 500:
                    logger.error("GestãoDS server error", 
                               status_code=response.status_code,
                               response_text=response.text)
                    metrics.increment("gestaods_server_errors")
                    raise GestaoDSConnectionError(f"GestãoDS server error: {response.status_code}")
                
                elif response.status_code >= 400:
                    logger.error("GestãoDS client error", 
                               status_code=response.status_code,
                               response_text=response.text)
                    metrics.increment("gestaods_client_errors")
                    raise GestaoDSError(f"GestãoDS client error: {response.status_code}")
                
                # Sucesso
                metrics.increment("gestaods_requests_success")
                return response.json()
                
        except httpx.TimeoutException as e:
            logger.error("GestãoDS request timeout", error=str(e))
            metrics.increment("gestaods_timeout_errors")
            raise GestaoDSConnectionError(f"Request timeout: {e}")
        
        except httpx.ConnectError as e:
            logger.error("GestãoDS connection error", error=str(e))
            metrics.increment("gestaods_connection_errors")
            raise GestaoDSConnectionError(f"Connection error: {e}")
        
        except Exception as e:
            logger.error("Unexpected GestãoDS API error", error=str(e))
            metrics.increment("gestaods_unknown_errors")
            raise GestaoDSError(f"Unexpected error: {e}")
    
    async def get_patient(self, cpf: str) -> Optional[Dict]:
        """Busca paciente por CPF"""
        # Verifica cache primeiro
        if cpf in self._patient_cache:
            cache_entry = self._patient_cache[cpf]
            if time.time() - cache_entry['timestamp'] < 300:  # 5 minutos
                logger.debug("Patient found in cache", cpf=cpf)
                return cache_entry['data']
        
        try:
            endpoint = f"api/dev-paciente/{self.token}/{cpf}/"
            result = await self._make_request("GET", endpoint)
            
            # Salva no cache
            self._patient_cache[cpf] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.info("Patient found in GestãoDS", cpf=cpf)
            return result
            
        except GestaoDSPatientNotFoundError:
            logger.info("Patient not found in GestãoDS", cpf=cpf)
            return None
        except Exception as e:
            logger.error("Failed to get patient", cpf=cpf, error=str(e))
            return None
    
    async def get_available_dates(self) -> List[str]:
        """Busca datas disponíveis"""
        try:
            endpoint = f"api/dev-agendamento/dias-disponiveis/{self.token}"
            result = await self._make_request("GET", endpoint)
            
            # Extrai datas da resposta
            dates = result.get('dias_disponiveis', [])
            logger.info("Available dates retrieved", count=len(dates))
            return dates
            
        except Exception as e:
            logger.error("Failed to get available dates", error=str(e))
            return []
    
    async def get_available_times(self, date: str) -> List[str]:
        """Busca horários disponíveis para uma data"""
        cache_key = f"times_{date}"
        
        # Verifica cache primeiro
        if cache_key in self._schedule_cache:
            cache_entry = self._schedule_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < 120:  # 2 minutos
                logger.debug("Times found in cache", date=date)
                return cache_entry['data']
        
        try:
            endpoint = f"api/dev-agendamento/horarios-disponiveis/{self.token}"
            params = {"data": date}
            result = await self._make_request("GET", endpoint, params=params)
            
            # Extrai horários da resposta
            times = result.get('horarios_disponiveis', [])
            
            # Salva no cache
            self._schedule_cache[cache_key] = {
                'data': times,
                'timestamp': time.time()
            }
            
            logger.info("Available times retrieved", date=date, count=len(times))
            return times
            
        except Exception as e:
            logger.error("Failed to get available times", date=date, error=str(e))
            return []
    
    async def create_appointment(self, appointment_data: Dict) -> Optional[Dict]:
        """Cria agendamento"""
        try:
            endpoint = f"api/dev-agendamento/agendar/"
            payload = {
                "token": self.token,
                **appointment_data
            }
            
            result = await self._make_request("POST", endpoint, json=payload)
            
            # Invalida cache de horários para a data
            date = appointment_data.get('data')
            if date:
                cache_key = f"times_{date}"
                self._schedule_cache.pop(cache_key, None)
            
            logger.info("Appointment created successfully", 
                       patient=appointment_data.get('paciente_nome'),
                       date=date)
            
            metrics.increment("gestaods_appointments_created")
            return result
            
        except Exception as e:
            logger.error("Failed to create appointment", 
                        appointment_data=appointment_data, error=str(e))
            metrics.increment("gestaods_appointment_creation_failed")
            return None
    
    async def reschedule_appointment(self, appointment_id: str, new_date: str, new_time: str) -> Optional[Dict]:
        """Reagenda consulta"""
        try:
            endpoint = f"api/dev-agendamento/reagendar/"
            payload = {
                "token": self.token,
                "agendamento_id": appointment_id,
                "nova_data": new_date,
                "novo_horario": new_time
            }
            
            result = await self._make_request("PUT", endpoint, json=payload)
            
            logger.info("Appointment rescheduled successfully", 
                       appointment_id=appointment_id,
                       new_date=new_date,
                       new_time=new_time)
            
            metrics.increment("gestaods_appointments_rescheduled")
            return result
            
        except Exception as e:
            logger.error("Failed to reschedule appointment", 
                        appointment_id=appointment_id, error=str(e))
            metrics.increment("gestaods_appointment_reschedule_failed")
            return None
    
    async def get_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Busca agendamento específico"""
        try:
            endpoint = f"api/dev-agendamento/retornar-agendamento/"
            params = {"token": self.token, "agendamento_id": appointment_id}
            result = await self._make_request("GET", endpoint, params=params)
            
            logger.debug("Appointment retrieved", appointment_id=appointment_id)
            return result
            
        except Exception as e:
            logger.error("Failed to get appointment", 
                        appointment_id=appointment_id, error=str(e))
            return None
    
    async def check_connection(self) -> bool:
        """Verifica se a API GestãoDS está disponível"""
        try:
            # Tenta buscar datas disponíveis como health check
            await self.get_available_dates()
            metrics.set("gestaods_connection_status", 1)
            return True
        except Exception as e:
            logger.error("GestãoDS connection check failed", error=str(e))
            metrics.set("gestaods_connection_status", 0)
            return False

# Singleton instance
_gestaods_service = None

async def get_gestaods_service() -> GestaoDSService:
    """Retorna instância singleton do GestãoDS service"""
    global _gestaods_service
    if _gestaods_service is None:
        _gestaods_service = GestaoDSService()
    return _gestaods_service 