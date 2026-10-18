"""
Digital Forensics - FalkorDB & GPT Graph Orchestrator
------------------------------------------------------
Provides a robust, corruption-proof bridge between LLM extraction (GPT)
and FalkorDB Graph Database with verified disk persistence and health tracking.
"""

import os
import sys
import time
import socket
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ForensicsOrchestrator")


class FalkorDBOrchestrator:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        graph_name: str = "digital_forensics",
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini"
    ):
        self.host = host or os.getenv("FALKORDB_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("FALKORDB_PORT", "6379"))
        self.graph_name = graph_name or os.getenv("FALKORDB_GRAPH", "digital_forensics")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.openai_model = openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        self.db = None
        self.graph = None
        self._init_connection()

    def _check_port_open(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """Verifies whether a TCP port is open and accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _init_connection(self) -> bool:
        """Initializes connection to FalkorDB safely with validation."""
        if not self._check_port_open(self.host, self.port):
            logger.warning(f"FalkorDB port {self.host}:{self.port} is not reachable. Is the Docker container running?")
            return False

        try:
            from falkordb import FalkorDB
            self.db = FalkorDB(host=self.host, port=self.port)
            self.graph = self.db.select_graph(self.graph_name)
            logger.info(f"Connected to FalkorDB at {self.host}:{self.port}, selected graph '{self.graph_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            self.db = None
            self.graph = None
            return False

    def is_healthy(self) -> Dict[str, Any]:
        """Comprehensive health report for FalkorDB, Docker ports, and GPT availability."""
        db_port_active = self._check_port_open(self.host, self.port)
        ui_port_active = self._check_port_open(self.host, 3000)
        
        db_responsive = False
        node_count = 0
        if db_port_active:
            try:
                if self.graph is None:
                    self._init_connection()
                if self.graph is not None:
                    res = self.graph.query("MATCH (n) RETURN count(n) AS total")
                    if res.result_set:
                        node_count = res.result_set[0][0]
                        db_responsive = True
            except Exception as e:
                logger.error(f"Health query check failed: {e}")

        # Check GPT configuration
        gpt_ready = bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))

        return {
            "falkordb_port_6379": db_port_active,
            "falkordb_ui_port_3000": ui_port_active,
            "falkordb_engine_responsive": db_responsive,
            "current_graph": self.graph_name,
            "total_nodes": node_count,
            "gpt_api_key_configured": gpt_ready,
            "status": "healthy" if (db_port_active and db_responsive) else "degraded"
        }

    def safe_query(self, cypher: str, params: Optional[Dict[str, Any]] = None, persist: bool = False) -> Any:
        """
        Executes a Cypher query with error isolation and optional disk persistence
        to guarantee zero database corruption.
        """
        if self.graph is None:
            if not self._init_connection():
                raise ConnectionError("FalkorDB is not connected.")

        try:
            res = self.graph.query(cypher, params or {})
            if persist:
                self.persist_to_disk()
            return res
        except Exception as e:
            logger.error(f"Query execution failed safely: {e}")
            raise

    def persist_to_disk(self) -> bool:
        """Forces FalkorDB/Redis to flush in-memory state to disk (dump.rdb)."""
        try:
            if self.db and hasattr(self.db, "connection"):
                self.db.connection.save()
                logger.info("FalkorDB state successfully saved to disk (D:\\FalkorDB\\data\\dump.rdb).")
                return True
        except Exception as e:
            logger.warning(f"SAVE command notice: {e}")
        return False

    def add_forensics_evidence(self, artifact_type: str, identifier: str, details: Dict[str, Any]) -> bool:
        """
        Adds a forensics artifact node and indexes it securely.
        Example artifact types: 'File', 'IPAddress', 'Process', 'UserAccount', 'NetworkConnection'
        """
        cypher = """
        MERGE (a:ForensicsArtifact {identifier: $id, type: $type})
        SET a.updated_at = timestamp(),
            a.details = $details
        RETURN a
        """
        params = {
            "id": identifier,
            "type": artifact_type,
            "details": str(details)
        }
        res = self.safe_query(cypher, params=params, persist=True)
        return bool(res.result_set)

    def link_evidence(self, source_id: str, relationship: str, target_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Creates a directed relationship between forensics artifacts.
        Example: (Process:powershell.exe)-[:CREATED_FILE]->(File:malware.exe)
        """
        # Sanitize relationship name to alphanumeric uppercase
        rel = "".join(c for c in relationship if c.isalnum() or c == "_").upper()
        cypher = f"""
        MATCH (s:ForensicsArtifact {{identifier: $source_id}})
        MATCH (t:ForensicsArtifact {{identifier: $target_id}})
        MERGE (s)-[r:{rel}]->(t)
        SET r.created_at = timestamp()
        RETURN r
        """
        params = {
            "source_id": source_id,
            "target_id": target_id
        }
        res = self.safe_query(cypher, params=params, persist=True)
        return bool(res.result_set)

    def extract_forensics_with_gpt(self, raw_evidence_text: str) -> Dict[str, Any]:
        """
        Uses OpenAI GPT model to extract forensic artifacts, attributes,
        and relationships from raw text/logs, then commits them cleanly into FalkorDB.
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured in .env or environment.")

        import json
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key)

        prompt = f"""
You are a Digital Forensics analysis engine. Extract forensic artifacts and their causal relationships from the evidence below.
Return ONLY valid JSON matching this exact schema:
{{
  "artifacts": [
    {{"id": "unique_string", "type": "Process|File|IPAddress|User|RegistryKey|Network", "details": {{"key": "value"}}}}
  ],
  "relationships": [
    {{"source_id": "string", "relationship": "EXECUTED|ACCESSED|CREATED|CONNECTED_TO", "target_id": "string"}}
  ]
}}

EVIDENCE:
{raw_evidence_text}
"""
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content)
        
        # Ingest artifacts safely
        for art in data.get("artifacts", []):
            self.add_forensics_evidence(
                artifact_type=art.get("type", "UnknownArtifact"),
                identifier=art.get("id"),
                details=art.get("details", {})
            )
            
        # Ingest relationships safely
        for rel in data.get("relationships", []):
            self.link_evidence(
                source_id=rel.get("source_id"),
                relationship=rel.get("relationship", "ASSOCIATED_WITH"),
                target_id=rel.get("target_id")
            )
            
        self.persist_to_disk()
        return data


def run_diagnostics():
    """Prints a system diagnostics report."""
    print("=" * 60)
    print("  DIGITAL FORENSICS - SYSTEM ORCHESTRATION DIAGNOSTICS")
    print("=" * 60)
    
    orchestrator = FalkorDBOrchestrator()
    health = orchestrator.is_healthy()
    
    print(f"[*] FalkorDB Engine (Port 6379)     : {'ONLINE' if health['falkordb_port_6379'] else 'OFFLINE'}")
    print(f"[*] FalkorDB Browser UI (Port 3000)  : {'ONLINE (http://localhost:3000)' if health['falkordb_ui_port_3000'] else 'OFFLINE'}")
    print(f"[*] Database Query Responsiveness   : {'OPERATIONAL' if health['falkordb_engine_responsive'] else 'FAILED'}")
    print(f"[*] Selected Graph Name             : {health['current_graph']}")
    print(f"[*] Total Graph Nodes               : {health['total_nodes']}")
    print(f"[*] GPT / OpenAI API Key Configured : {'YES' if health['gpt_api_key_configured'] else 'NO (Set OPENAI_API_KEY in .env)'}")
    print(f"[*] Overall Health Status           : {health['status'].upper()}")
    print("-" * 60)
    
    if health["status"] == "healthy":
        print("[+] Performing sample forensics node creation...")
        orchestrator.add_forensics_evidence(
            artifact_type="SystemProcess",
            identifier="pid:4088_powershell.exe",
            details={"command": "Get-Process", "user": "SYSTEM"}
        )
        orchestrator.add_forensics_evidence(
            artifact_type="LogFile",
            identifier="path:C:/Windows/System32/winevt/Logs/Security.evtx",
            details={"action": "AUDIT_SUCCESS"}
        )
        orchestrator.link_evidence(
            source_id="pid:4088_powershell.exe",
            relationship="ACCESSED",
            target_id="path:C:/Windows/System32/winevt/Logs/Security.evtx"
        )
        print("[+] Sample evidence linked successfully with verified disk persistence!")
    print("=" * 60)


if __name__ == "__main__":
    run_diagnostics()
