# Digital Forensics - FalkorDB & GPT Orchestration

## 1. System Status & Verification

- **FalkorDB Container**: Active and Running (`falkordb`)
- **Redis / Graph Port**: `127.0.0.1:6379` (Verified responding to Cypher queries)
- **Web UI Browser**: `http://localhost:3000` (FalkorDB GUI)
- **Data Persistence**: `D:\FalkorDB\data\dump.rdb` mapped to `/var/lib/falkordb/data`
- **Docker Path**: `D:\Docker\DockerDesktop\resources\bin` added to User `PATH`.
- **Python SDK**: `falkordb` library installed in Conda environment.

---

## 2. Quick Management Commands

### Start / Stop Container
Using Docker Compose:
```powershell
docker compose up -d
```
To stop safely without corruption:
```powershell
docker compose down
```

### Check Container Status
```powershell
docker ps
```

---

## 3. Running the Orchestrator

The orchestration layer (`orchestrator.py`) provides corruption-proof graph operations, health monitoring, and GPT log extraction.

### Run System Diagnostics & Self-Test:
```powershell
python orchestrator.py
```

### Using with OpenAI / GPT:
1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Insert your OpenAI API key in `.env`:
   ```ini
   OPENAI_API_KEY=sk-...
   ```
3. Use `extract_forensics_with_gpt()` to analyze raw forensic evidence (process logs, network connections, authentication events) and automatically populate the FalkorDB knowledge graph.

---

## 4. Anti-Corruption Guarantees

1. **Volume Mount**: All graph data and journal logs are written to physical disk at `D:\FalkorDB\data`.
2. **Explicit Persistence**: The orchestrator triggers safe `SAVE` operations after batch operations to guarantee persistence.
3. **Graceful Restarts**: The container uses `--restart unless-stopped` with standard shutdown signal handling.
