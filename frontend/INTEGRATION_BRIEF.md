┌─ INTEGRATION BRIEF ─────────────────────────────────────────────────────┐
│ API Base URL env var : PUBLIC_API_URL (default: http://localhost:8000)  │
│ Auth method          : BYOK Bearer Token via OS Keyring (X-GRIS-Provider)│
│ Endpoints consumed   : [POST /api/analysis/start, GET /api/analysis/:id,│
│                        POST /api/chat, GET /api/history, POST /api/export]│
│ WebSocket needed     : Yes (ws://localhost:8000/ws/stream-{id})          │
│ Environment file     : .env.local (template included in frontend root)  │
└─────────────────────────────────────────────────────────────────────────┘

## Backend to Frontend Data Contract

1. **Repository Analysis Payload**:
   - `url`: GitHub HTTPS URL string
   - `depth`: 'quick' | 'deep' | 'recreation'
   - `spdxId`: Detected repository SPDX license identifier

2. **Streamed Tokens & AST Progress**:
   - WebSocket `/ws/stream-{id}` emits JSON event chunks for AST parsing progress and recreation prompt token streaming.

3. **Attribution Block (SDG-4 Protocol)**:
   - Output payload must preserve source repository URL, date, and license disclaimer in exports.
