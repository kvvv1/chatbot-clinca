import time
import asyncio
from typing import Optional, Callable, Any
from contextlib import asynccontextmanager
import structlog

logger = structlog.get_logger(__name__)

class CircuitBreakerError(Exception):
    """Exceção lançada quando o circuit breaker está aberto"""
    pass

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        
        # Estado do circuit breaker
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        # Métricas
        self.total_requests = 0
        self.failed_requests = 0
        self.successful_requests = 0
    
    def _can_attempt_reset(self) -> bool:
        """Verifica se pode tentar resetar o circuit breaker"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Chamado quando uma operação é bem-sucedida"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        self.successful_requests += 1
        
        logger.debug("Circuit breaker success", 
                    name=self.name, 
                    failure_count=self.failure_count)
    
    def _on_failure(self):
        """Chamado quando uma operação falha"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.failed_requests += 1
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker opened", 
                          name=self.name, 
                          failure_count=self.failure_count,
                          threshold=self.failure_threshold)
        else:
            logger.debug("Circuit breaker failure", 
                        name=self.name, 
                        failure_count=self.failure_count)
    
    @asynccontextmanager
    async def __call__(self):
        """Context manager para usar o circuit breaker"""
        if self.state == "OPEN":
            if self._can_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker attempting reset", name=self.name)
            else:
                logger.warning("Circuit breaker is open, request blocked", 
                              name=self.name,
                              time_until_reset=self.recovery_timeout - (time.time() - self.last_failure_time))
                raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
        
        self.total_requests += 1
        
        try:
            yield
            self._on_success()
        except Exception as e:
            self._on_failure()
            raise
    
    def get_metrics(self) -> dict:
        """Retorna métricas do circuit breaker"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "successful_requests": self.successful_requests,
            "failure_rate": self.failed_requests / max(self.total_requests, 1),
            "last_failure_time": self.last_failure_time
        }
    
    def reset(self):
        """Reset manual do circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker manually reset", name=self.name) 