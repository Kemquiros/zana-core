#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'; RESET='\033[0m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'

banner() {
cat << 'EOF'
        [ X A N A   N O D O   A P E X ]
     Instalación del Sistema Cognitivo Soberano
EOF
}

require() { command -v "$1" &>/dev/null || { echo -e "${RED}✗ Falta: $1${RESET}"; exit 1; }; }

banner
echo ""
require docker
docker compose version &>/dev/null || { echo -e "${RED}✗ docker compose plugin no encontrado${RESET}"; exit 1; }

# ── Generar .env si no existe ────────────────────────────────
if [ ! -f .env ]; then
  echo -e "${CYAN}▶ Generando .env desde .env.example...${RESET}"
  cp .env.example .env
  # Sobrescribir secretos con valores aleatorios
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 16)|" .env
  sed -i "s|^NEO4J_PASSWORD=.*|NEO4J_PASSWORD=$(openssl rand -hex 12)|" .env
  echo -e "${GREEN}✓ .env creado. Agrega ANTHROPIC_API_KEY si usas Claude como fallback.${RESET}"
fi

# Cargar variables del .env para usarlas en este script
set -a; source .env; set +a

# ── Directorios de datos ─────────────────────────────────────
mkdir -p data/{chroma,postgres,redis,neo4j/data,caddy}

# ── Build e inicio ───────────────────────────────────────────
echo -e "${CYAN}▶ Construyendo imágenes...${RESET}"
docker compose build --parallel

echo -e "${CYAN}▶ Levantando Nodo Apex...${RESET}"
docker compose up -d

# ── Resumen ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  XANA NODO APEX — ONLINE${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  PWA:      ${CYAN}http://localhost:${XANA_PWA_PORT:-54448}${RESET}"
echo -e "  Gateway:  ${CYAN}http://localhost:${XANA_GATEWAY_PORT:-54446}/health${RESET}"
echo -e "  Chroma:   ${CYAN}http://localhost:${XANA_CHROMA_PORT:-58001}${RESET}"
echo -e "  Postgres: ${CYAN}localhost:${XANA_POSTGRES_PORT:-55433}${RESET}"
echo -e "  Redis:    ${CYAN}localhost:${XANA_REDIS_PORT:-56380}${RESET}"
echo -e "  Neo4j:    ${CYAN}http://localhost:${XANA_NEO4J_HTTP_PORT:-57474}${RESET}"
echo ""
echo -e "  Para ver logs: ${BOLD}docker compose logs -f gateway${RESET}"
echo -e "  Para detener:  ${BOLD}docker compose down${RESET}"
echo ""
