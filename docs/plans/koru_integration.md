# Architecture Plan: KoruOS Integration & N8N Sandbox

## Phase 1: Real-time Communication (AION WebSockets/SSE)
**Goal**: Migrate Aria UI's polling architecture to real-time events.
- **Current State**: `zana-core/aria-ui/app/page.tsx` polls `http://localhost:51112/ai/forge/genome` every 10 seconds.
- **New State**: Use `EventSource` (SSE) or `WebSocket` to maintain a persistent connection to KoruOS.
- **Task 1**: Update the React `useEffect` to listen to an SSE stream on `http://localhost:51112/ai/forge/genome/stream` (or similar). The component should handle connection drops and auto-reconnects gracefully.

## Phase 2: Hardened N8N Sandbox Deployment
**Goal**: Integrate N8N into the `zana-core` Docker stack as a secure execution layer for workflows.
- **Current State**: N8N is absent from the local stack.
- **New State**: Add `n8n` service to `zana-core/docker-compose.yml`.
- **Requirements**:
  - Secure, isolated environment variables for N8N.
  - Persistent volume for N8N data.
  - Health checks.
  - Integration with the `caddy` proxy if required, or exposed securely on a specific port (e.g., `5678`).

## Execution
- **Agent 1 (Frontend)**: Implement the SSE/WebSocket logic in `Aria UI`.
- **Agent 2 (DevOps)**: Add N8N to the `docker-compose.yml` file.
- **Review**: Ensure no ESLint errors in UI, and a valid Docker Compose configuration.