# XANA Deployment Guide

Three tiers depending on budget and requirements.

---

## Tier 1 — Free / Local + ngrok (Development & Demo)

**Cost:** $0/month  
**Audience:** Personal use, demos, development  
**Limitation:** Requires your machine to be on; no persistent domain

### Setup

```bash
# 1. Start infrastructure
cd zana-core
docker compose up -d

# 2. Start gateway
cd sensory
uv run uvicorn multimodal_gateway:app --host 0.0.0.0 --port 54446

# 3. Expose publicly with ngrok
ngrok http 54446
# → You get a URL like https://abc123.ngrok.io
```

Set `XANA_PUBLIC_URL=https://abc123.ngrok.io` in `.env` so the A2A AgentCard is correct.

### Limitations
- URL changes every ngrok restart (free plan)
- Machine must stay on
- No TLS termination on the gateway (ngrok handles it)

---

## Tier 2 — Medium / VPS (~$10–20/month)

**Cost:** ~$12–20 USD/month  
**Audience:** Always-on personal assistant, small teams  
**Recommended providers:** DigitalOcean, Hetzner, Contabo, Linode

### Recommended specs

| Provider | Plan | Cost | RAM | CPU |
|----------|------|------|-----|-----|
| Hetzner CX22 | Cloud | $5/mo | 4 GB | 2 vCPU |
| DigitalOcean Basic | Droplet | $12/mo | 2 GB | 1 vCPU |
| Contabo VPS S | Cloud | $7/mo | 8 GB | 4 vCPU |

**Recommended:** Hetzner CX32 ($12/mo, 8 GB RAM) — enough for Docker stack + Python gateway + local Ollama (small models).

### Setup

```bash
# On your VPS (Ubuntu 22.04+)

# 1. Install dependencies
apt update && apt install -y docker.io docker-compose-plugin uv git

# 2. Clone
git clone https://github.com/kemquiros/zana-core.git
cd zana-core
cp .env.example .env
# Edit .env — set your domain and API keys

# 3. Set your domain in .env
XANA_DOMAIN=xana.yourdomain.com
XANA_PUBLIC_URL=https://xana.yourdomain.com

# 4. Start everything (Caddy handles TLS automatically)
docker compose up -d

# 5. Point your DNS A record to your VPS IP
# xana.yourdomain.com → <VPS IP>
```

Caddy (included in `docker-compose.yml`) automatically provisions a Let's Encrypt TLS certificate.

### Ports that must be open

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 | TCP | HTTP → redirect to HTTPS |
| 443 | TCP | HTTPS (Caddy) |

All internal service ports (5xxxx) remain closed to the internet.

### Optional: Local LLM with Ollama

```bash
# Install Ollama on the VPS
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (llama3.2:3b fits on 8 GB RAM)
ollama pull llama3.2:3b

# Set in .env
XANA_PRIMARY_MODEL=ollama/llama3.2:3b
OLLAMA_URL=http://localhost:11434
```

This makes XANA fully autonomous — no cloud API keys needed.

---

## Tier 3 — Scale / Cloud + Kubernetes

**Cost:** $100–500+/month depending on load  
**Audience:** Production deployment, multi-user, enterprise  
**Platforms:** AWS EKS, GCP GKE, Azure AKS, or DigitalOcean Kubernetes

### Architecture overview

```
Internet
  └── Load Balancer (HTTPS/443)
        └── Ingress Controller (nginx/traefik)
              ├── /sense/*        → xana-gateway Deployment (2–4 replicas)
              ├── /apex/*         → xana-gateway Deployment
              └── /.well-known/*  → xana-gateway Deployment

Cluster internal:
  xana-gateway → chromadb Service
              → postgres Service (StatefulSet)
              → redis Service
              → neo4j Service (StatefulSet)
              → symbiosis Service
```

### Helm / manifests (skeleton)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: xana-gateway
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: gateway
        image: your-registry/xana-gateway:v1.0.0
        ports:
        - containerPort: 54446
        envFrom:
        - secretRef:
            name: xana-secrets
        - configMapRef:
            name: xana-config
```

### Secrets management

Never put API keys in manifests. Use:
- **AWS Secrets Manager** + External Secrets Operator
- **GCP Secret Manager** + Workload Identity
- **HashiCorp Vault**
- **Kubernetes Secrets** (base64, acceptable for internal clusters)

```bash
kubectl create secret generic xana-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-... \
  --from-literal=POSTGRES_PASSWORD=... \
  --from-literal=NEO4J_PASSWORD=...
```

### CI/CD pipeline (GitHub Actions skeleton)

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    tags: ['v*']
jobs:
  build-push:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Build and push Docker image
      run: |
        docker build -t your-registry/xana-gateway:${{ github.ref_name }} .
        docker push your-registry/xana-gateway:${{ github.ref_name }}
  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
    - name: Update k8s deployment
      run: |
        kubectl set image deployment/xana-gateway \
          gateway=your-registry/xana-gateway:${{ github.ref_name }}
```

### Cost estimates (AWS, 2025)

| Component | Service | Est. Cost |
|-----------|---------|-----------|
| Gateway (2 pods) | ECS Fargate | ~$30/mo |
| PostgreSQL | RDS t3.micro | ~$15/mo |
| Redis | ElastiCache t3.micro | ~$15/mo |
| ChromaDB | ECS Fargate | ~$10/mo |
| Neo4j | EC2 t3.small | ~$15/mo |
| Load Balancer | ALB | ~$20/mo |
| **Total** | | **~$105/mo** |

For GPU inference (local LLM at scale), add a `g4dn.xlarge` EC2 instance (~$150/mo) with Ollama.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional* | Anthropic Claude API key |
| `XANA_PRIMARY_MODEL` | Yes | LiteLLM model string |
| `XANA_PUBLIC_URL` | Yes | Public base URL of this node |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `XANA_DOMAIN` | Tier 2+ | Domain for Caddy TLS |
| `AEON_VOICE` | No | TTS voice (default: `es-CO-GonzaloNeural`) |
| `OLLAMA_URL` | No | Ollama base URL for local LLM |

*At least one LLM provider key is needed unless using Ollama locally.

---

## Health Check Endpoint

```bash
GET /health
```

Returns JSON with all backend statuses. Use this for load balancer health checks and monitoring.

```json
{
  "status": "online",
  "backends": {
    "stt": "faster-whisper",
    "tts": "edge-tts",
    "llm": "anthropic/claude-3-5-haiku-20241022",
    "vision": "claude-vision",
    "kalman": "rust-steel-core",
    "armor": "rust"
  }
}
```
