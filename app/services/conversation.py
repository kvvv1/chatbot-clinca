import asyncio
import time
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from app.config import get_settings
from app.utils.validators import validar_cpf, extrair_cpf_da_mensagem
from app.utils.monitoring import metrics
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()

# Cache em memória para estados ativos
active_conversations = {}

class ConversationManager:
    def __init__(self):
        self.states = {
            "inicio": self._handle_inicio,
            "aguardando_cpf": self._handle_cpf,
            "escolhendo_data": self._handle_escolha_data,
            "escolhendo_horario": self._handle_escolha_horario,
            "confirmando_agendamento": self._handle_confirmacao,
            "visualizando_agendamentos": self._handle_visualizar_agendamentos,
            "lista_espera": self._handle_lista_espera,
            "falando_atendente": self._handle_falar_atendente
        }
        
        # Comandos globais que funcionam em qualquer estado
        self.global_commands = {
            "menu": "inicio",
            "0": "inicio",
            "voltar": "inicio",
            "cancelar": "inicio",
            "sair": "inicio",
            "ajuda": "inicio"
        }
    
    async def get_conversation_state(self, phone: str) -> Tuple[str, Dict]:
        """Obtém estado da conversa (memória primeiro, depois banco)"""
        # 1. Tenta memória primeiro (< 1ms)
        if phone in active_conversations:
            state_data = active_conversations[phone]
            if time.time() - state_data['timestamp'] < settings.cache_ttl_conversation:
                return state_data['state'], state_data['context']
        
        # 2. Fallback para banco (< 50ms)
        # TODO: Implementar busca no banco
        return "inicio", {}
    
    async def update_state(self, phone: str, state: str, context: Dict = None):
        """Atualiza estado da conversa (memória + async DB write)"""
        if context is None:
            context = {}
        
        # Update em memória
        active_conversations[phone] = {
            'state': state,
            'context': context,
            'timestamp': time.time()
        }
        
        # Async DB write (não bloqueia)
        asyncio.create_task(self._persist_to_db(phone, state, context))
        
        logger.debug("Conversation state updated", 
                    phone=phone, state=state, context_keys=list(context.keys()))
    
    async def _persist_to_db(self, phone: str, state: str, context: Dict):
        """Persiste estado no banco de dados"""
        try:
            # TODO: Implementar persistência no banco
            pass
        except Exception as e:
            logger.error("Failed to persist conversation state", 
                        phone=phone, error=str(e))
    
    async def quick_validate(self, message: str) -> bool:
        """Pré-validação rápida antes de processar"""
        # Regras rápidas sem I/O
        if len(message) > 100:  # Muito longo
            return False
        if message.count('http') > 0:  # Links suspeitos
            return False
        if message.count('@') > 2:  # Muitos @
            return False
        return True
    
    async def process_message(self, phone: str, message: str) -> str:
        """Processa mensagem e retorna resposta"""
        start_time = time.time()
        
        try:
            # Pré-validação rápida
            if not await self.quick_validate(message):
                return "❌ Mensagem muito longa ou inválida. Por favor, tente novamente."
            
            # Normaliza mensagem
            message = message.strip().lower()
            
            # Verifica comandos globais
            if message in self.global_commands:
                await self.update_state(phone, self.global_commands[message])
                return await self._handle_inicio(phone, message)
            
            # Obtém estado atual
            current_state, context = await self.get_conversation_state(phone)
            
            # Processa com handler específico
            if current_state in self.states:
                response = await self.states[current_state](phone, message, context)
            else:
                # Estado desconhecido, volta ao início
                await self.update_state(phone, "inicio")
                response = await self._handle_inicio(phone, message)
            
            # Métricas
            elapsed_time = time.time() - start_time
            metrics.record("conversation_response_time", elapsed_time)
            
            logger.info("Message processed successfully", 
                       phone=phone, 
                       state=current_state,
                       response_time=elapsed_time)
            
            return response
            
        except Exception as e:
            logger.error("Failed to process message", 
                        phone=phone, message=message, error=str(e))
            metrics.increment("conversation_processing_errors")
            return "😅 Ops! Algo deu errado. Tente novamente ou digite 'menu' para voltar ao início."
    
    async def _handle_inicio(self, phone: str, message: str, context: Dict = None) -> str:
        """Handler para estado inicial"""
        await self.update_state(phone, "inicio", {})
        
        # Saudação contextual
        hora = datetime.now().hour
        if 5 <= hora < 12:
            saudacao = "🌅 Bom dia"
        elif 12 <= hora < 18:
            saudacao = "🌞 Boa tarde"
        else:
            saudacao = "🌙 Boa noite"
        
        return f"""{saudacao}! Bem-vindo(a) à *Clínica Gabriela Nassif*! 🏥

Sou seu assistente virtual. Como posso ajudar?

*1️⃣* - Agendar consulta
*2️⃣* - Ver meus agendamentos  
*3️⃣* - Cancelar consulta
*4️⃣* - Lista de espera
*5️⃣* - Falar com atendente

Digite o número da opção desejada."""
    
    async def _handle_menu_principal(self, phone: str, message: str, context: Dict) -> str:
        """Processa opção do menu principal"""
        if message == "1":
            await self.update_state(phone, "aguardando_cpf", context)
            return """📋 *Agendamento de Consulta*

Por favor, informe seu CPF (apenas números):

Exemplo: 12345678901"""
        
        elif message == "2":
            await self.update_state(phone, "visualizando_agendamentos", context)
            return "🔍 Buscando seus agendamentos..."
        
        elif message == "3":
            return "❌ Funcionalidade em desenvolvimento. Entre em contato: (31) 9860-0366"
        
        elif message == "4":
            await self.update_state(phone, "lista_espera", context)
            return "📋 *Lista de Espera*\n\nFuncionalidade em desenvolvimento."
        
        elif message == "5":
            await self.update_state(phone, "falando_atendente", context)
            return f"""👨‍💼 *Falar com Atendente*

Para falar diretamente com um atendente, ligue:

📞 *{settings.clinic_phone}*

Horário de atendimento:
🕐 Segunda a Sexta: 8h às 18h
🕐 Sábado: 8h às 12h"""
        
        else:
            return """❌ Opção inválida!

Digite apenas o número da opção desejada:

*1️⃣* - Agendar consulta
*2️⃣* - Ver meus agendamentos  
*3️⃣* - Cancelar consulta
*4️⃣* - Lista de espera
*5️⃣* - Falar com atendente"""
    
    async def _handle_cpf(self, phone: str, message: str, context: Dict) -> str:
        """Handler para validação de CPF"""
        # Extrai CPF da mensagem
        cpf = extrair_cpf_da_mensagem(message)
        
        if not cpf:
            return """❌ CPF inválido!

Por favor, informe seu CPF corretamente (apenas números):

Exemplo: 12345678901

Ou digite 'menu' para voltar ao início."""
        
        # Valida CPF
        if not validar_cpf(cpf):
            return """❌ CPF inválido!

O CPF informado não é válido. Verifique e tente novamente.

Ou digite 'menu' para voltar ao início."""
        
        # TODO: Buscar paciente no GestãoDS
        # Por enquanto, simula paciente encontrado
        context['cpf'] = cpf
        context['patient_name'] = "Paciente Teste"  # Será substituído pela busca real
        
        await self.update_state(phone, "escolhendo_data", context)
        
        return f"""✅ CPF validado com sucesso!

👤 Paciente: {context['patient_name']}
📋 CPF: {cpf}

Agora vamos escolher a data da consulta. Digite 'menu' para voltar ao início."""
    
    async def _handle_escolha_data(self, phone: str, message: str, context: Dict) -> str:
        """Handler para escolha de data"""
        # TODO: Buscar datas disponíveis no GestãoDS
        # Por enquanto, simula datas disponíveis
        datas_disponiveis = [
            "15/12/2024",
            "16/12/2024", 
            "17/12/2024",
            "18/12/2024",
            "19/12/2024"
        ]
        
        context['available_dates'] = datas_disponiveis
        
        await self.update_state(phone, "escolhendo_horario", context)
        
        return f"""📅 *Datas Disponíveis*

Escolha uma das datas disponíveis:

1️⃣ - 15/12/2024 (Domingo)
2️⃣ - 16/12/2024 (Segunda)
3️⃣ - 17/12/2024 (Terça)
4️⃣ - 18/12/2024 (Quarta)
5️⃣ - 19/12/2024 (Quinta)

Digite o número da data desejada ou 'menu' para voltar."""
    
    async def _handle_escolha_horario(self, phone: str, message: str, context: Dict) -> str:
        """Handler para escolha de horário"""
        # TODO: Buscar horários disponíveis no GestãoDS
        # Por enquanto, simula horários disponíveis
        horarios_disponiveis = [
            "08:00", "09:00", "10:00", "11:00",
            "14:00", "15:00", "16:00", "17:00"
        ]
        
        context['available_times'] = horarios_disponiveis
        context['selected_date'] = "15/12/2024"  # Será a data escolhida
        
        await self.update_state(phone, "confirmando_agendamento", context)
        
        return f"""⏰ *Horários Disponíveis*

Escolha um horário para {context['selected_date']}:

1️⃣ - 08:00
2️⃣ - 09:00
3️⃣ - 10:00
4️⃣ - 11:00
5️⃣ - 14:00
6️⃣ - 15:00
7️⃣ - 16:00
8️⃣ - 17:00

Digite o número do horário desejado ou 'menu' para voltar."""
    
    async def _handle_confirmacao(self, phone: str, message: str, context: Dict) -> str:
        """Handler para confirmação de agendamento"""
        context['selected_time'] = "09:00"  # Será o horário escolhido
        
        # TODO: Criar agendamento no GestãoDS
        # Por enquanto, simula sucesso
        
        await self.update_state(phone, "inicio", {})
        
        return f"""✅ *Consulta agendada com sucesso!*

📋 *Detalhes do agendamento:*
👤 Paciente: {context.get('patient_name', 'N/A')}
📅 Data: {context.get('selected_date', 'N/A')}
⏰ Horário: {context.get('selected_time', 'N/A')}
👩‍⚕️ Profissional: Dra. Gabriela Nassif

📍 *Endereço:*
{settings.clinic_name}
{settings.clinic_address}

💡 *Lembretes:*
• Chegue com 15 minutos de antecedência
• Traga documento com foto
• Traga carteira do convênio (se aplicável)

Você receberá um lembrete 24h antes da consulta.

Digite 'menu' para voltar ao início."""
    
    async def _handle_visualizar_agendamentos(self, phone: str, message: str, context: Dict) -> str:
        """Handler para visualizar agendamentos"""
        # TODO: Buscar agendamentos no GestãoDS
        await self.update_state(phone, "inicio", {})
        
        return """📋 *Seus Agendamentos*

Nenhum agendamento encontrado.

Para agendar uma consulta, digite 'menu' e escolha a opção 1."""
    
    async def _handle_lista_espera(self, phone: str, message: str, context: Dict) -> str:
        """Handler para lista de espera"""
        await self.update_state(phone, "inicio", {})
        
        return """📋 *Lista de Espera*

Funcionalidade em desenvolvimento.

Para agendar uma consulta, digite 'menu' e escolha a opção 1."""
    
    async def _handle_falar_atendente(self, phone: str, message: str, context: Dict) -> str:
        """Handler para falar com atendente"""
        await self.update_state(phone, "inicio", {})
        
        return f"""👨‍💼 *Falar com Atendente*

Para falar diretamente com um atendente, ligue:

📞 *{settings.clinic_phone}*

Horário de atendimento:
🕐 Segunda a Sexta: 8h às 18h
🕐 Sábado: 8h às 12h

Digite 'menu' para voltar ao início."""

# Singleton instance
_conversation_manager = None

async def get_conversation_manager() -> ConversationManager:
    """Retorna instância singleton do conversation manager"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager 