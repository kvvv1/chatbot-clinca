import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.conversation import ConversationManager
from app.services.whatsapp import WhatsAppService
from app.services.gestaods import GestaoDSService

@pytest.mark.asyncio
class TestConversationFlow:
    """Testes de fluxo completo de conversação"""
    
    async def test_fluxo_agendamento_completo(self):
        """Testa fluxo completo de agendamento"""
        conversation_manager = ConversationManager()
        
        # Simula conversa completa
        phone = "5511999999999"
        
        # 1. Mensagem inicial
        response1 = await conversation_manager.process_message(phone, "oi")
        assert "Bem-vindo" in response1
        assert "1️⃣" in response1
        
        # 2. Escolhe agendar consulta
        response2 = await conversation_manager.process_message(phone, "1")
        assert "CPF" in response2
        
        # 3. Informa CPF válido
        response3 = await conversation_manager.process_message(phone, "12345678909")
        assert "CPF validado" in response3
        
        # 4. Escolhe data
        response4 = await conversation_manager.process_message(phone, "1")
        assert "Datas Disponíveis" in response4
        
        # 5. Escolhe horário
        response5 = await conversation_manager.process_message(phone, "1")
        assert "Horários Disponíveis" in response5
        
        # 6. Confirma agendamento
        response6 = await conversation_manager.process_message(phone, "1")
        assert "Consulta agendada" in response6
    
    async def test_comandos_globais(self):
        """Testa comandos que funcionam em qualquer estado"""
        conversation_manager = ConversationManager()
        phone = "5511999999999"
        
        # Avança para estado intermediário
        await conversation_manager.process_message(phone, "1")  # Escolhe agendar
        
        # Testa comando menu
        response = await conversation_manager.process_message(phone, "menu")
        assert "Bem-vindo" in response
        
        # Verifica se voltou ao estado inicial
        state, context = await conversation_manager.get_conversation_state(phone)
        assert state == "inicio"
    
    async def test_validacao_mensagem(self):
        """Testa validação de mensagens"""
        conversation_manager = ConversationManager()
        phone = "5511999999999"
        
        # Mensagem muito longa
        long_message = "a" * 200
        response = await conversation_manager.process_message(phone, long_message)
        assert "Muito longa" in response
        
        # Mensagem com links suspeitos
        suspicious_message = "Clique aqui: http://malicious.com"
        response = await conversation_manager.process_message(phone, suspicious_message)
        assert "inválida" in response

@pytest.mark.asyncio
class TestWhatsAppService:
    """Testes do serviço WhatsApp"""
    
    @patch('app.services.whatsapp.httpx.AsyncClient')
    async def test_send_message_success(self, mock_client):
        """Testa envio bem-sucedido de mensagem"""
        # Mock da resposta
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messageId": "test123"}
        mock_response.content = b"{}"
        
        mock_client.return_value.request.return_value = mock_response
        
        service = WhatsAppService()
        result = await service.send_text("5511999999999", "Teste")
        
        assert result is not None
        assert result["messageId"] == "test123"
    
    @patch('app.services.whatsapp.httpx.AsyncClient')
    async def test_send_message_error(self, mock_client):
        """Testa erro no envio de mensagem"""
        # Mock de erro
        mock_client.return_value.request.side_effect = Exception("Network error")
        
        service = WhatsAppService()
        result = await service.send_text("5511999999999", "Teste")
        
        assert result is None
    
    def test_format_phone(self):
        """Testa formatação de telefone"""
        service = WhatsAppService()
        
        # Testa diferentes formatos
        test_cases = [
            ("11999999999", "5511999999999@c.us"),
            ("+5511999999999", "5511999999999@c.us"),
            ("(11) 99999-9999", "5511999999999@c.us"),
        ]
        
        for input_phone, expected in test_cases:
            result = service._format_phone(input_phone)
            assert result == expected

@pytest.mark.asyncio
class TestGestaoDSService:
    """Testes do serviço GestãoDS"""
    
    @patch('app.services.gestaods.httpx.AsyncClient')
    async def test_get_patient_success(self, mock_client):
        """Testa busca bem-sucedida de paciente"""
        # Mock da resposta
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nome": "João Silva",
            "cpf": "12345678909",
            "telefone": "11999999999"
        }
        mock_response.content = b"{}"
        
        mock_client.return_value.request.return_value = mock_response
        
        service = GestaoDSService()
        result = await service.get_patient("12345678909")
        
        assert result is not None
        assert result["nome"] == "João Silva"
    
    @patch('app.services.gestaods.httpx.AsyncClient')
    async def test_get_available_dates(self, mock_client):
        """Testa busca de datas disponíveis"""
        # Mock da resposta
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "dias_disponiveis": ["15/12/2024", "16/12/2024", "17/12/2024"]
        }
        mock_response.content = b"{}"
        
        mock_client.return_value.request.return_value = mock_response
        
        service = GestaoDSService()
        result = await service.get_available_dates()
        
        assert len(result) == 3
        assert "15/12/2024" in result

@pytest.mark.asyncio
class TestWebhookHandlers:
    """Testes dos handlers de webhook"""
    
    async def test_webhook_message_handler(self):
        """Testa handler de mensagem recebida"""
        from app.handlers.webhook import handle_message
        from app.handlers.webhook import WebhookMessage
        
        # Mock dos serviços
        with patch('app.handlers.webhook.get_whatsapp_service') as mock_whatsapp, \
             patch('app.handlers.webhook.get_conversation_manager') as mock_conversation:
            
            # Mock do WhatsApp service
            mock_whatsapp_service = AsyncMock()
            mock_whatsapp.return_value = mock_whatsapp_service
            
            # Mock do conversation manager
            mock_conversation_manager = AsyncMock()
            mock_conversation_manager.process_message.return_value = "Resposta teste"
            mock_conversation.return_value = mock_conversation_manager
            
            # Dados do webhook
            webhook_data = WebhookMessage(
                type="ReceivedCallback",
                phone="5511999999999@c.us",
                text={"message": "oi"},
                messageId="msg123"
            )
            
            # Executa handler
            result = await handle_message(webhook_data)
            
            # Verifica resultado
            assert result["status"] == "success"
            assert result["response_sent"] == True
            
            # Verifica se marcou como lida
            mock_whatsapp_service.mark_as_read.assert_called_once()
            
            # Verifica se processou mensagem
            mock_conversation_manager.process_message.assert_called_once()
            
            # Verifica se enviou resposta
            mock_whatsapp_service.send_text.assert_called_once()

@pytest.mark.asyncio
class TestErrorHandling:
    """Testes de tratamento de erros"""
    
    async def test_circuit_breaker(self):
        """Testa circuit breaker"""
        from app.utils.circuit_breaker import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Simula falhas
        for _ in range(2):
            try:
                async with circuit_breaker:
                    raise Exception("Test error")
            except Exception:
                pass
        
        # Verifica se circuit breaker abriu
        assert circuit_breaker.state == "OPEN"
        
        # Aguarda recovery
        import time
        time.sleep(1.1)
        
        # Verifica se tentou reset
        assert circuit_breaker.state == "HALF_OPEN"
    
    async def test_retry_mechanism(self):
        """Testa mecanismo de retry"""
        from tenacity import retry, stop_after_attempt, wait_exponential
        
        call_count = 0
        
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=3))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        # Executa função que falha
        try:
            await failing_function()
        except Exception:
            pass
        
        # Verifica se tentou 3 vezes
        assert call_count == 3 