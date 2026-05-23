# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
# Use `npm ci` when a lockfile exists, otherwise fall back to `npm install`.
# This prevents CI/build failures when `package-lock.json` is not committed.
RUN if [ -f package-lock.json ]; then \
      npm ci --frozen-lockfile; \
    else \
      npm install; \
    fi

COPY . .
RUN npm run build

# ── Stage 2: Nginx serving ────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove default nginx static files
RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
  CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
