FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Phát triển cục bộ: docker-compose.yml bind-mount mã nguồn đè lên /app.
FROM deps AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM deps AS builder
# Next.js standalone ghi rewrite và proxyTimeout vào bản dựng, nên địa chỉ API nội bộ
# phải được truyền lúc build chứ không phải lúc chạy.
ARG API_PROXY_TARGET=http://api:8000
ARG API_PROXY_TIMEOUT_MS=180000
ENV API_PROXY_TARGET=$API_PROXY_TARGET \
    API_PROXY_TIMEOUT_MS=$API_PROXY_TIMEOUT_MS \
    NEXT_TELEMETRY_DISABLED=1
COPY . .
RUN npm run build

# Bản triển khai: chỉ chứa máy chủ standalone, chạy bằng người dùng không có quyền root.
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
RUN addgroup -S -g 10001 web && adduser -S -D -H -u 10001 -G web web
COPY --from=builder --chown=web:web /app/.next/standalone ./
COPY --from=builder --chown=web:web /app/.next/static ./.next/static
USER web
EXPOSE 3000
CMD ["node", "server.js"]
