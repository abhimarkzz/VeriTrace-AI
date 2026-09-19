# ==============================================================================
# VeriTrace AI — Frontend Service Multi-Stage Dockerfile
# ==============================================================================

# --- Stage 1: Build production assets with Node.js ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install build dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source files
COPY index.html tsconfig.json vite.config.ts ./
COPY public/ public/
COPY src/ src/

# Build optimized static bundle
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# --- Stage 2: Serve optimized assets with Nginx ---
FROM nginx:alpine AS runner

# Remove default nginx html
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx reverse proxy configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy compiled artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
