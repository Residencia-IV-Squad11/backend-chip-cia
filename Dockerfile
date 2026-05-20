# Dockerfile para produção (multistage build)
FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN npm install -g pnpm && pnpm install

COPY . .

RUN npm run build

# ──────────────────────────────────────────
# Etapa 2: Servir com Flask
# ──────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

# Copiar requirements do backend
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY . .

# Copiar build do frontend
COPY --from=builder /app/dist ./static

EXPOSE 5000

CMD ["python", "app.py"]
