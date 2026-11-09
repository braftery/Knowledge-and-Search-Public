# One image. The web client is built only when web/package.json exists.
# The API then serves web/dist, or a placeholder page until that build exists.

FROM node:22-bookworm-slim AS web
WORKDIR /src
COPY web ./web
RUN if [ -f web/package.json ]; then \
      cd web && \
      if [ -f package-lock.json ]; then npm ci; else npm install; fi && \
      npm run build; \
    else \
      mkdir -p web/dist; \
    fi

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt
COPY . .
COPY --from=web /src/web/dist ./web/dist
EXPOSE 8000
CMD ["python", "-m", "api"]
