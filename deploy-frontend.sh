#!/bin/sh
# Rebuild y redeploy del frontend en producción
# Uso: ./deploy-frontend.sh

set -e
cd "$(dirname "$0")"

echo "🔨 Building frontend..."
docker run --rm \
  -v "$(pwd)/frontend:/app" \
  -v "$(pwd)/frontend/node_modules:/app/node_modules" \
  -w /app \
  -e VITE_API_URL=/api/v1 \
  node:20-alpine \
  sh -c "npm install && npm run build"

echo "🔄 Reloading nginx..."
docker exec audiomedia_nginx nginx -s reload

echo "✅ Deploy completado"
