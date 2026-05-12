# chip_e_cia — API de Análise de Qualidade de Atendimento

API REST em Flask que analisa transcrições de atendimento ao cliente
usando IA (Groq / Llama 3) e persiste métricas em MySQL.

**🆕 Com Frontend React integrado!**

---

## 📁 Estrutura do Projeto

```
chip_e_cia/
├── app.py                        # Ponto de entrada Flask
├── config.py                     # Configuração do app e SQLAlchemy
├── models.py                     # Modelos ORM (todas as tabelas)
├── routes.py                     # Blueprints e endpoints REST
├── services/
│   ├── __init__.py
│   ├── groq_service.py           # Integração com a API do Groq
│   └── atendimento_service.py    # Orquestração: LLM → DB
├── requirements.txt
├── .env.example                  # Template de variáveis de ambiente
└── README.md
```

---

## ⚙️ Pré-requisitos

| Ferramenta | Versão mínima |
|------------|---------------|
| Python     | 3.10+         |
| MySQL      | 8.0+          |
| Conta Groq | API key ativa |

---

## 🚀 Instalação Passo a Passo

### 1. Clone e entre na pasta
```bash
git clone <seu-repositório>
cd chip_e_cia
```

### 2. Crie e ative o ambiente virtual
```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` e preencha:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=chip_e_cia
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

> Atenção: não deixe `GROQ_API_KEY` com o valor de placeholder. Substitua por sua chave real do Groq, caso contrário a análise retornará erro de configuração.

### 5. Crie o banco de dados MySQL
```sql
CREATE DATABASE IF NOT EXISTS chip_e_cia;
```
> As tabelas são criadas automaticamente pelo `db.create_all()` ao iniciar a aplicação.

### 6. Inicie a API
```bash
python app.py
```
Saída esperada:
```
2024-XX-XX XX:XX:XX  INFO     __main__ — Tabelas verificadas/criadas com sucesso.
 * Running on http://0.0.0.0:5000
```

### 7. (Opcional) Inicie o Frontend

O frontend React está integrado na pasta `frontend/`. Para desenvolvimento:

```bash
cd frontend
npm install              # ou: pnpm install
npm run dev             # Roda em http://localhost:5173
```

O backend já está configurado com CORS para aceitar requisições do frontend.

Para produção, compile o frontend e copie para a pasta `static/`:
```bash
npm run build
xcopy dist\* ..\static\ /E /I /Y   # Windows
# ou: cp -r dist/* ../static/      # Linux/Mac
```

Veja [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) para instruções completas.

---

## 📡 Endpoints

### `GET /health`
Health check básico.
```json
{ "status": "ok", "service": "chip_e_cia API" }
```

---

### `POST /api/atendimento/avaliar`
Analisa uma conversa via Groq e salva no banco.

**Request:**
```json
{
  "texto_conversa": "Atendente: Olá, tudo bem? Como posso ajudar?\nCliente: Quero cancelar meu plano..."
}
```

**Response 201:**
```json
{
  "sucesso": true,
  "atendimento_id": 42,
  "score_final": 7.25,
  "mensagem": "Atendimento analisado e salvo com sucesso."
}
```

**Códigos de erro:**
| Código | Causa |
|--------|-------|
| 400    | Campo `texto_conversa` ausente ou muito curto |
| 422    | LLM retornou JSON inválido |
| 502    | Falha na comunicação com a API do Groq |
| 500    | Erro interno (ex: banco offline) |

---

### `GET /api/atendimento/<id>`
Retorna o detalhe completo de um atendimento.

**Response 200:**
```json
{
  "sucesso": true,
  "dados": {
    "id": 42,
    "resumo": "Cliente solicitou cancelamento do plano pós-pago...",
    "data_criacao": "2024-07-10T14:30:00",
    "classificacao": {
      "categoria": "Cancelamento",
      "intencao": "Cancelamento",
      "sentimento": "Negativo",
      "criticidade": "Alta",
      "sla": "4 horas"
    },
    "qualidade": {
      "empatia": 8,
      "clareza": 7,
      "objetividade": 6,
      "resolutividade": 5,
      "score_final": 6.5
    },
    "topicos": [
      { "id": 1, "nome": "Cancelamento de plano" },
      { "id": 2, "nome": "Insatisfação com cobrança" }
    ]
  }
}
```

---

### `GET /api/atendimento/listar?page=1&per_page=20`
Lista atendimentos com paginação.

---

### `GET /api/dashboard/resumo`
Agrega dados para o dashboard principal.

**Response 200:**
```json
{
  "sucesso": true,
  "dados": {
    "total_atendimentos": 150,
    "media_score_final": 7.43,
    "distribuicao_sentimento": [
      { "sentimento": "Positivo", "total": 80 },
      { "sentimento": "Negativo", "total": 45 },
      { "sentimento": "Neutro",   "total": 25 }
    ],
    "top_categorias": [
      { "categoria": "Suporte Técnico", "total": 60 },
      { "categoria": "Cancelamento",    "total": 35 }
    ],
    "evolucao_score_diaria": [
      { "data": "2024-07-08", "media_score": 7.1, "total": 12 },
      { "data": "2024-07-09", "media_score": 7.5, "total": 18 }
    ]
  }
}
```

---

### `GET /api/dashboard/qualidade`
Média de cada dimensão de qualidade.

```json
{
  "sucesso": true,
  "dados": {
    "empatia": 7.8,
    "clareza": 7.2,
    "objetividade": 6.9,
    "resolutividade": 6.5
  }
}
```

---

## 🧪 Testando com cURL

```bash
# Health check
curl http://localhost:5000/health

# Avaliar atendimento
curl -X POST http://localhost:5000/api/atendimento/avaliar \
  -H "Content-Type: application/json" \
  -d '{
    "texto_conversa": "Atendente: Bom dia! Meu nome é Carlos, como posso ajudá-lo?\nCliente: Oi, estou com problemas para acessar minha conta. Já tentei várias vezes e não consigo entrar.\nAtendente: Entendo sua frustração. Pode me informar seu CPF para eu verificar?\nCliente: Claro, é 123.456.789-00.\nAtendente: Localizei sua conta. Vou resetar sua senha agora. Em 5 minutos você receberá um e-mail.\nCliente: Ótimo, obrigado pela ajuda rápida!"
  }'

# Resumo do dashboard
curl http://localhost:5000/api/dashboard/resumo
```

---

## 🐳 Docker (opcional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
docker build -t chip-e-cia-api .
docker run -p 5000:5000 --env-file .env chip-e-cia-api
```
