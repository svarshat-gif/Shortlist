FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./frontend
COPY public ./public
COPY index.html vite.config.js ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-compile -r requirements.txt
COPY backend ./backend
COPY samples ./samples
COPY --from=frontend /app/dist ./dist
RUN mkdir -p data inbox
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
