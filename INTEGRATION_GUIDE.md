# 🚀 Guia de Integração Frontend + Backend

Este projeto é uma integração monorepo com frontend React (TypeScript) e backend Flask (Python).

---

## 📁 Estrutura do Projeto

```
chip-e-cia/
├── app.py                    # Ponto de entrada Flask
├── config.py                 # Configuração
├── models.py                 # Modelos ORM
├── routes.py                 # API routes
├── services/                 # Lógica de negócio
├── frontend/                 # React + TypeScript + Vite
│   ├── src/                 # Código-fonte
│   ├── package.json         
│   ├── vite.config.ts       
│   ├── .env                 # Vars de ambiente
│   └── dist/                # Build compilado (produção)
├── static/                  # Arquivos estáticos servidos pelo Flask
├── .env                     # Backend vars
└── README.md
```

---

## 🛠️ Instalação & Setup

### Opção 1: Desenvolvimento (Recomendado)

**Backend e Frontend rodando em portas separadas com auto-reload.**

#### Backend (Flask)

```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
python app.py
# Roda em http://localhost:5000
```

#### Frontend (React + Vite)

**Requisitos:** Node.js 18+ e npm/pnpm

```bash
cd frontend

# Instalar dependências
npm install
# ou pnpm install

# Iniciar dev server
npm run dev
# Roda em http://localhost:5173
```

**Resultado:**
- Backend: `http://localhost:5000` ✅
- Frontend: `http://localhost:5173` ✅
- CORS já configurado no backend para aceitar requisições do frontend

---

### Opção 2: Produção (Build único)

#### 1. Compilar Frontend

```bash
cd frontend
npm install
npm run build
# Gera arquivos em: frontend/dist/
```

#### 2. Copiar arquivos para Backend

```bash
# Do diretório raiz do projeto:
xcopy frontend\dist\* static\ /E /I /Y  # Windows
# ou
cp -r frontend/dist/* static/            # Linux/Mac
```

#### 3. Servir via Flask

```bash
# Backend já serve os arquivos estáticos automaticamente
python app.py
# Acesse: http://localhost:5000
```

---

## 🔗 API Communication

### Frontend → Backend

O frontend está configurado para fazer requisições para o backend via `VITE_API_BASE_URL`.

**Exemplo (src/lib/api.ts):**
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export async function fetchDashboard() {
  const response = await fetch(`${API_BASE}/api/dashboard/resumo`);
  return response.json();
}
```

### Variáveis de Ambiente

**Frontend (.env):**
```
VITE_API_BASE_URL=http://localhost:5000  # Dev
# ou
VITE_API_BASE_URL=https://api.chip-cia.com  # Produção
```

**Backend (.env):**
```
DB_HOST=localhost
DB_USER=root
GROQ_API_KEY=gsk_xxxxx
```

---

## 🐳 Docker (Opcional)

Se preferir containerizar ambos:

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml .
RUN npm install
COPY frontend . 
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=builder /app/frontend/dist ./static
EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
docker build -t chip-cia-app .
docker run -p 5000:5000 --env-file .env chip-cia-app
```

---

## 📊 Endpoints Disponíveis

### Backend Only

- `GET /health` - Health check
- `POST /api/atendimento/avaliar` - Analisar conversa
- `GET /api/atendimento/<id>` - Detalhe atendimento
- `GET /api/dashboard/resumo` - Resumo dashboard
- `GET /api/dashboard/qualidade` - Métricas qualidade

### Frontend Integrado

- `GET /` - Serve o index.html do React
- Static files (CSS, JS, imagens) - Servidos automaticamente

---

## 🔄 Workflow de Desenvolvimento

1. **Terminal 1 - Backend:**
   ```bash
   .venv\Scripts\activate
   python app.py
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Browser:**
   ```
   Acesse: http://localhost:5173
   ```

4. **Fazer alterações** → Vite auto-recarrega
5. **API calls** → Vão para `http://localhost:5000` (CORS ✅)

---

## 🚢 Deploy em Produção

1. Build do frontend
2. Copiar `dist/` para pasta `static/`
3. Fazer push ao seu repositório
4. Deploy no servidor (Heroku, AWS, etc)

Flask automaticamente serve os arquivos estáticos.

---

## ❓ Troubleshooting

### CORS Error no Frontend

✅ **Solução:** O CORS já está configurado em `config.py`

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Porta 5000 já em uso

```bash
# Encontre e mate o processo
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Frontend não encontra API

- Verificar `.env` do frontend tem `VITE_API_BASE_URL` correto
- Backend está rodando? `curl http://localhost:5000/health`

---

## 📚 Recursos

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

