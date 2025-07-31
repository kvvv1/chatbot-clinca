# 🤖 Chatbot WhatsApp - Clínica Gabriela Nassif

Chatbot inteligente para agendamento de consultas médicas via WhatsApp, integrado com Z-API Enterprise e sistema GestãoDS.

## 🚀 Características

- ✅ **99.99% de entrega** com Z-API Enterprise
- ✅ **Integração completa** com GestãoDS
- ✅ **Validação robusta** de CPF e dados brasileiros
- ✅ **Circuit Breaker** para proteção contra falhas
- ✅ **Cache inteligente** para performance
- ✅ **Logs estruturados** e monitoramento
- ✅ **Health checks** automáticos
- ✅ **Deploy otimizado** com Docker

## 📋 Pré-requisitos

- Python 3.11+
- Docker e Docker Compose (opcional)
- Conta Z-API Enterprise
- Acesso à API GestãoDS
- Banco Supabase (opcional)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone <repository-url>
cd chatbot-clinica
```

### 2. Configure as variáveis de ambiente
```bash
cp env.example .env
# Edite o arquivo .env com suas credenciais
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Execute a aplicação
```bash
# Desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🐳 Deploy com Docker

### Desenvolvimento
```bash
docker-compose up --build
```

### Produção
```bash
# Build da imagem
docker build -t chatbot-clinica .

# Executar container
docker run -d \
  --name chatbot-clinica \
  -p 8000:8000 \
  --env-file .env \
  chatbot-clinica
```

## 🔗 Configuração de Webhooks

### Z-API Webhooks
Configure os seguintes webhooks no painel Z-API:

1. **Mensagens recebidas:**
   ```
   URL: https://seu-dominio.com/api/v1/webhook/message
   Método: POST
   ```

2. **Status de entrega:**
   ```
   URL: https://seu-dominio.com/api/v1/webhook/status
   Método: POST
   ```

3. **Status de conexão:**
   ```
   URL: https://seu-dominio.com/api/v1/webhook/connected
   Método: POST
   ```

## 📊 Endpoints da API

### Health Check
```bash
GET /health
```

### Dashboard
```bash
GET /dashboard
```

### Métricas
```bash
GET /metrics
```

### Webhooks
```bash
POST /api/v1/webhook/message
POST /api/v1/webhook/status
POST /api/v1/webhook/connected
```

### Administrativos
```bash
POST /admin/send-message?phone=5511999999999&message=Teste
POST /admin/reset-conversation/{phone}
```

## 🏥 Fluxo de Agendamento

1. **Saudação** - Bot apresenta menu principal
2. **Validação CPF** - Verifica CPF e busca paciente
3. **Escolha de Data** - Mostra datas disponíveis
4. **Escolha de Horário** - Mostra horários disponíveis
5. **Confirmação** - Cria agendamento no GestãoDS
6. **Confirmação Final** - Envia detalhes da consulta

## 🔧 Configuração de Variáveis

### Z-API
```env
ZAPI_INSTANCE_ID=3E4F7360B552F0C2DBCB9E6774402775
ZAPI_TOKEN=17829E98BB59E9ADD55BBBA9
ZAPI_CLIENT_TOKEN=F909fc109aad54566bf42a6d09f00a8dbS
ZAPI_BASE_URL=https://api.z-api.io
```

### GestãoDS
```env
GESTAODS_API_URL=https://apidev.gestaods.com.br
GESTAODS_TOKEN=733a8e19a94b65d58390da380ac946b6d603a535
```

### Supabase
```env
SUPABASE_URL=https://feqylqrphdpeeusdyeyw.supabase.co
SUPABASE_ANON_KEY=sua_chave_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_aqui
```

### Clínica
```env
CLINIC_NAME=Clínica Gabriela Nassif
CLINIC_PHONE=+553198600366
CLINIC_ADDRESS=Endereço da Clínica
```

## 🧪 Testes

### Testes Unitários
```bash
pytest tests/ -v
```

### Testes de Integração
```bash
pytest tests/integration/ -v
```

### Testes de Carga
```bash
pytest tests/load/ -v
```

## 📈 Monitoramento

### Métricas Disponíveis
- Mensagens processadas/hora
- Tempo de resposta médio
- Taxa de erro por endpoint
- Status de conexões (WhatsApp, GestãoDS)
- Agendamentos criados/dia

### Logs
Os logs são estruturados em JSON e incluem:
- Request ID único
- Telefone mascarado
- Estado da conversa
- Tempo de resposta
- Erros detalhados

### Alertas
- WhatsApp desconectado
- API GestãoDS indisponível
- Alto volume de erros
- Falha no envio de lembretes

## 🚨 Comandos de Emergência

### Via WhatsApp
```
ADMIN:STATUS - Status do sistema
ADMIN:RESET:{phone} - Reset de conversa
```

### Via API
```bash
# Reset de conversa
POST /admin/reset-conversation/{phone}

# Envio de mensagem de teste
POST /admin/send-message?phone={phone}&message={message}
```

## 🔒 Segurança

- ✅ Dados sensíveis mascarados em logs
- ✅ Validação rigorosa de inputs
- ✅ Rate limiting (30 req/min)
- ✅ Circuit breaker para proteção
- ✅ Usuário não-root no Docker
- ✅ Health checks automáticos

## 📞 Suporte

**Clínica:** Gabriela Nassif  
**WhatsApp:** +553198600366  
**Email:** contato@clinicanassif.com.br

## 📄 Licença

Este projeto é proprietário da Clínica Gabriela Nassif.

## 🔄 Changelog

### v1.0.0
- ✅ Implementação inicial
- ✅ Integração Z-API Enterprise
- ✅ Integração GestãoDS
- ✅ Sistema de conversação
- ✅ Monitoramento e logs
- ✅ Deploy com Docker

---

*Desenvolvido especificamente para a Clínica Gabriela Nassif* 