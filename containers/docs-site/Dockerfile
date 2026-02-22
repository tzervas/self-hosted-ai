# Multi-stage build: MkDocs (build) -> nginx (serve)
# Build context must be the repository root (self-hosted-ai/)

# Stage 1: Build static site with MkDocs Material
FROM python:3.12-slim AS builder

WORKDIR /build

# Install MkDocs and plugins
RUN pip install --no-cache-dir \
    mkdocs-material==9.6.* \
    mkdocs-minify-plugin==0.8.* \
    pymdown-extensions==10.* \
    pillow \
    cairosvg

# Copy MkDocs configuration
COPY mkdocs.yml .

# Copy documentation source
COPY mkdocs-docs/ docs/

# Build static site
RUN mkdocs build --strict

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine

# Security: run as non-root
RUN addgroup -g 1001 -S nginx-user && \
    adduser -u 1001 -S nginx-user -G nginx-user && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx-user:nginx-user /var/run/nginx.pid

# Custom nginx config for SPA and security headers
COPY containers/docs-site/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built site from builder stage
COPY --from=builder /build/site /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

EXPOSE 8080

USER nginx-user

CMD ["nginx", "-g", "daemon off;"]
