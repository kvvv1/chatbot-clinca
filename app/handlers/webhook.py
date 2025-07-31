from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.whatsapp import get_whatsapp_service
from app.services.conversation import get_conversation_manager
from app.utils.validators import mascarar_dados_sensiveis
from app.utils.monitoring import metrics
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

class WebhookMessage(BaseModel):
    type: str
    phone: Optional[str] = None
    text: Optional[Dict] = None
    messageId: Optional[str] = None
    status: Optional[str] = None
    connected: Optional[bool] = None

@router.post("/webhook/message")
async def handle_message(webhook_data: WebhookMessage):
    """Handler para mensagens recebidas do Z-API"""
    try:
        # Log da mensagem recebida (dados mascarados)
        masked_phone = mascarar_dados_sensiveis(webhook_data.phone or "")
        logger.info("Webhook message received", 
                   type=webhook_data.type,
                   phone=masked_phone,
                   message_id=webhook_data.messageId)
        
        # Incrementa métrica
        metrics.increment("webhook_messages_received")
        
        # Verifica se é mensagem de texto
        if webhook_data.type != "ReceivedCallback":
            logger.debug("Ignoring non-text message", type=webhook_data.type)
            return {"status": "ignored", "reason": "not_text_message"}
        
        # Extrai dados da mensagem
        phone = webhook_data.phone
        message_text = webhook_data.text.get("message", "") if webhook_data.text else ""
        message_id = webhook_data.messageId
        
        if not phone or not message_text:
            logger.warning("Invalid message data", phone=phone, text=message_text)
            return {"status": "error", "reason": "invalid_data"}
        
        # Remove sufixo @c.us do telefone
        phone = phone.replace("@c.us", "")
        
        # Marca mensagem como lida
        whatsapp_service = await get_whatsapp_service()
        await whatsapp_service.mark_as_read(phone, message_id)
        
        # Processa mensagem com conversation manager
        conversation_manager = await get_conversation_manager()
        response = await conversation_manager.process_message(phone, message_text)
        
        # Envia resposta
        if response:
            await whatsapp_service.send_text(phone, response)
            logger.info("Response sent successfully", 
                       phone=masked_phone,
                       response_length=len(response))
            metrics.increment("webhook_responses_sent")
        
        return {"status": "success", "response_sent": bool(response)}
        
    except Exception as e:
        logger.error("Error processing webhook message", 
                    error=str(e),
                    webhook_data=webhook_data.dict())
        metrics.increment("webhook_processing_errors")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/status")
async def handle_status(webhook_data: WebhookMessage):
    """Handler para status de entrega de mensagens"""
    try:
        logger.info("Message status update", 
                   message_id=webhook_data.messageId,
                   status=webhook_data.status)
        
        # Incrementa métricas baseadas no status
        if webhook_data.status:
            metrics.increment(f"message_status_{webhook_data.status.lower()}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Error processing status webhook", error=str(e))
        metrics.increment("webhook_status_errors")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/connected")
async def handle_connection(webhook_data: WebhookMessage):
    """Handler para status de conexão do WhatsApp"""
    try:
        connected = webhook_data.connected
        logger.info("WhatsApp connection status", connected=connected)
        
        # Atualiza métrica de status de conexão
        if connected is not None:
            metrics.set("whatsapp_connection_status", 1 if connected else 0)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Error processing connection webhook", error=str(e))
        metrics.increment("webhook_connection_errors")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/webhook/health")
async def webhook_health():
    """Health check para webhooks"""
    return {
        "status": "healthy",
        "webhooks": {
            "message": "/webhook/message",
            "status": "/webhook/status", 
            "connected": "/webhook/connected"
        }
    } 