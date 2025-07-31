import time
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger(__name__)

class Metrics:
    def __init__(self):
        self._counters = defaultdict(int)
        self._gauges = {}
        self._histograms = defaultdict(list)
        self._start_time = time.time()
        
        # Histórico de métricas (últimas 1000 entradas)
        self._history = deque(maxlen=1000)
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Incrementa um contador"""
        key = self._build_key(metric_name, tags)
        self._counters[key] += value
        
        self._record_metric("counter", metric_name, value, tags)
        logger.debug("Metric incremented", metric=metric_name, value=value, tags=tags)
    
    def set(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Define um valor de gauge"""
        key = self._build_key(metric_name, tags)
        self._gauges[key] = value
        
        self._record_metric("gauge", metric_name, value, tags)
        logger.debug("Metric set", metric=metric_name, value=value, tags=tags)
    
    def record(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra um valor para histograma"""
        key = self._build_key(metric_name, tags)
        self._histograms[key].append(value)
        
        # Mantém apenas os últimos 100 valores
        if len(self._histograms[key]) > 100:
            self._histograms[key] = self._histograms[key][-100:]
        
        self._record_metric("histogram", metric_name, value, tags)
        logger.debug("Metric recorded", metric=metric_name, value=value, tags=tags)
    
    def _build_key(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Constrói chave única para métrica com tags"""
        if not tags:
            return metric_name
        
        tag_str = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        return f"{metric_name}:{tag_str}"
    
    def _record_metric(self, metric_type: str, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra métrica no histórico"""
        self._history.append({
            "timestamp": time.time(),
            "type": metric_type,
            "name": name,
            "value": value,
            "tags": tags or {}
        })
    
    def get_counter(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Obtém valor de um contador"""
        key = self._build_key(metric_name, tags)
        return self._counters.get(key, 0)
    
    def get_gauge(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Obtém valor de um gauge"""
        key = self._build_key(metric_name, tags)
        return self._gauges.get(key)
    
    def get_histogram_stats(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Obtém estatísticas de um histograma"""
        key = self._build_key(metric_name, tags)
        values = self._histograms.get(key, [])
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "p50": sorted(values)[len(values) // 2],
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)]
        }
    
    def get_uptime(self) -> float:
        """Retorna uptime da aplicação em segundos"""
        return time.time() - self._start_time
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Retorna todas as métricas"""
        return {
            "uptime": self.get_uptime(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name.split(":")[0])
                for name in self._histograms.keys()
            },
            "recent_metrics": list(self._history)[-100:]  # Últimas 100 métricas
        }
    
    def reset(self):
        """Reseta todas as métricas"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._history.clear()
        self._start_time = time.time()
        logger.info("Metrics reset")

# Instância global
metrics = Metrics() 