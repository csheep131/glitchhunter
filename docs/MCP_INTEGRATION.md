# SocratiCode MCP Integration

**Version:** 2.0
**Date:** April 13, 2026
**Status:** Architecture Specification

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [MCP Server Setup](#2-mcp-server-setup)
3. [LangGraph Tool Integration](#3-langgraph-tool-integration)
4. [SocratiCode Tools Reference](#4-socratiCode-tools-reference)
5. [Fallback Strategy](#5-fallback-strategy)
6. [Hardware-Specific Configuration](#6-hardware-specific-configuration)
7. [Testing Strategy](#7-testing-strategy)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOC RATICODE MCP INTEGRATION ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  GlitchHunter Application                                            │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ LangGraph State Machine                                        │  │   │
│  │  │                                                                 │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │ Tool Node: socratiCode_search                            │  │  │   │
│  │  │  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │  │   │
│  │  │  │ │ MCP Client  │──│ Tool Adapter│──│ Fallback    │       │  │  │   │
│  │  │  │ │             │  │             │  │ Manager     │       │  │  │   │
│  │  │  │ └─────────────┘  └─────────────┘  └─────────────┘       │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                 │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │ Tool Node: socratiCode_graph_query                       │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                 │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │ Tool Node: socratiCode_context_search                    │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                 │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │ Tool Node: socratiCode_circular                          │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              │ MCP Protocol (JSON-RPC)                       │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SocratiCode MCP Server                                              │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│  │  │ codebase_search │  │ codebase_graph  │  │ codebase_context│      │   │
│  │  │ (Hybrid Search) │  │ (Dependencies)  │  │ (Artifacts)     │      │   │
│  │  │                 │  │                 │  │                 │      │   │
│  │  │ • Semantic (RRF)│  │ • ast-grep      │  │ • DB Schemas    │      │   │
│  │  │ • BM25 (RRF)    │  │ • NetworkX      │  │ • API Specs     │      │   │
│  │  │ • Combined      │  │ • File locations│  │ • Infra Configs │      │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│  │  │ Vector DB       │  │ Dependency Graph│  │ Context Index   │      │   │
│  │  │ (Qdrant)        │  │ (ast-grep)      │  │ (Chunks)        │      │   │
│  │  │                 │  │                 │  │                 │      │   │
│  │  │ • 1536-d embed  │  │ • Polyglot      │  │ • Incremental   │      │   │
│  │  │ • KNN search    │  │ • Cross-file    │  │ • Auto-detect   │      │   │
│  │  │ • <10ms latency │  │ • Call chains   │  │ • Stale check   │      │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Fallback (if MCP unavailable):                                              │
│  ────────────────────                                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Local ChromaDB  │  │ Local NetworkX  │  │ Local Repomix   │              │
│  │ (Embeddings)    │  │ (Graphs)        │  │ (Context)       │              │
│  │                 │  │                 │  │                 │              │
│  │ • SQLite backend│  │ • Tree-sitter   │  │ • XML format    │              │
│  │ • Slower search │  │ • Single-language│ │ • Full context  │              │
│  │ • No RRF        │  │ • No cross-file │  │ • Larger tokens │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility | Interface |
|-----------|---------------|-----------|
| **MCP Client** | Connects to SocratiCode MCP server, handles JSON-RPC | `mcp.ClientSession` |
| **Tool Adapter** | Converts MCP tool calls to LangGraph tool format | LangGraph Tool Node |
| **Fallback Manager** | Activates local infrastructure when MCP unavailable | Internal API |
| **Local ChromaDB** | Fallback vector storage with SQLite backend | ChromaDB API |
| **Local NetworkX** | Fallback dependency graph using Tree-sitter | NetworkX API |
| **Local Repomix** | Fallback context packing in XML format | Repomix CLI |

### 1.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MCP INTEGRATION DATA FLOW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LangGraph Node Request                                                      │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  1. MCP Client                                                       │   │
│  │      • Check if MCP server is available                              │   │
│  │      • If yes: Send JSON-RPC request                                 │   │
│  │      • If no: Activate Fallback Manager                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ├─────────────────┐                                                │
│          │                 │                                                │
│          ▼ (MCP available) ▼ (MCP unavailable)                              │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │  SocratiCode    │  │  Fallback       │                                   │
│  │  MCP Server     │  │  Manager        │                                   │
│  │                 │  │                 │                                   │
│  │  • Hybrid search│  │  • Local search │                                   │
│  │  • RRF fusion   │  │  • BM25 only    │                                   │
│  │  • <10ms        │  │  • ~100ms       │                                   │
│  └────────┬────────┘  └────────┬────────┘                                   │
│           │                    │                                            │
│           ▼                    ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3. Result Normalization                                             │   │
│  │      • Convert to common result format                               │   │
│  │      • Add source metadata (MCP vs Fallback)                         │   │
│  │      • Include confidence scores                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  4. LangGraph State Update                                           │   │
│  │      • Add search results to state                                   │   │
│  │      • Include source information                                    │   │
│  │      • Continue pipeline                                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. MCP Server Setup

### 2.1 Installation

```bash
# scripts/setup_socratiCode.sh

#!/bin/bash
set -e

echo "=== SocratiCode MCP Setup ==="

# Configuration
SOCRATICODE_VERSION="0.2.0"
QDRANT_VERSION="1.9.0"
INSTALL_DIR="/opt/socratiCode"
CONFIG_DIR="/etc/socratiCode"

# 1. Clone SocratiCode repository
echo "Cloning SocratiCode ${SOCRATICODE_VERSION}..."
git clone https://github.com/giancarloerra/SocratiCode.git ${INSTALL_DIR}
cd ${INSTALL_DIR}
git checkout v${SOCRATICODE_VERSION}

# 2. Create virtual environment
echo "Creating Python virtual environment..."
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Qdrant (Docker)
echo "Starting Qdrant container..."
docker run -d \
  --name qdrant_socratiCode \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__GRPC_PORT=6334 \
  qdrant/qdrant:v${QDRANT_VERSION}

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to start..."
sleep 10

# 5. Create configuration directory
echo "Creating configuration..."
mkdir -p ${CONFIG_DIR}

cat > ${CONFIG_DIR}/config.yaml <<EOF
# SocratiCode Configuration

# Qdrant vector database
qdrant:
  host: localhost
  port: 6333
  grpc_port: 6334
  collection_name: glitchunter_codebase
  vector_size: 1536  # nomic-embed-text-v1.5
  distance: Cosine

# Ollama for embeddings
ollama:
  host: localhost
  port: 11434
  embedding_model: nomic-embed-text

# Indexing configuration
indexing:
  chunk_size: 512
  chunk_overlap: 50
  batch_size: 100
  languages:
    - python
    - javascript
    - typescript
    - rust
    - go
    - java
    - cpp

# MCP server configuration
mcp:
  host: localhost
  port: 8765
  log_level: info

# Graph configuration
graph:
  backend: ast-grep
  include_tests: false
  max_depth: 5
EOF

# 6. Download embedding model
echo "Downloading embedding model..."
ollama pull nomic-embed-text

# 7. Create systemd service (optional)
if [ -d /etc/systemd/system ]; then
    echo "Creating systemd service..."
    cat > /etc/systemd/system/socratiCode-mcp.service <<EOF
[Unit]
Description=SocratiCode MCP Server
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin"
ExecStart=${INSTALL_DIR}/venv/bin/python -m socratiCode.mcp_server --config ${CONFIG_DIR}/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable socratiCode-mcp
    systemctl start socratiCode-mcp
else
    echo "Systemd not available. Start manually with:"
    echo "  cd ${INSTALL_DIR} && source venv/bin/activate && python -m socratiCode.mcp_server --config ${CONFIG_DIR}/config.yaml"
fi

# 8. Verify installation
echo "Verifying installation..."
sleep 5
curl -s http://localhost:6333/api/v1/collections | jq '.' || echo "Qdrant not ready yet"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "SocratiCode MCP server configuration:"
echo "  - MCP Port: 8765"
echo "  - Qdrant Port: 6333 (HTTP), 6334 (gRPC)"
echo "  - Config: ${CONFIG_DIR}/config.yaml"
echo ""
echo "To start manually:"
echo "  cd ${INSTALL_DIR} && source venv/bin/activate && python -m socratiCode.mcp_server --config ${CONFIG_DIR}/config.yaml"
echo ""
```

### 2.2 Configuration

```yaml
# config.yaml - SocratiCode Section

mcp_integration:
  # Enable/disable MCP integration
  enabled: true

  # SocratiCode MCP server configuration
  server:
    host: localhost
    port: 8765
    timeout_seconds: 30
    retry_attempts: 3
    retry_delay_seconds: 5

  # SocratiCode-specific settings
  socratiCode:
    # Auto-index codebase on startup
    auto_index: true

    # Index on each run (incremental)
    index_on_start: false

    # Poll interval for indexing status (seconds)
    poll_interval_seconds: 60

    # Tools to enable
    tools:
      - codebase_search
      - codebase_graph_query
      - codebase_context_search
      - codebase_graph_circular
      - codebase_graph_stats
      - codebase_graph_visualize

    # Search configuration
    search:
      # Default number of results
      default_limit: 10

      # Minimum RRF score threshold (0-1)
      min_score: 0.1

      # Include linked projects
      include_linked_projects: false

      # Filter by language
      language_filter: null

      # Filter by file path
      file_filter: null

    # Graph configuration
    graph:
      # Include full symbol source code
      include_content: false

      # Maximum traversal depth
      max_depth: 3

      # Minimum confidence threshold
      min_confidence: 0.7

      # Include test files
      include_tests: false

    # Context configuration
    context:
      # Default number of results
      default_limit: 10

      # Minimum score threshold
      min_score: 0.1

      # Filter by artifact name
      artifact_filter: null

  # Fallback configuration
  fallback:
    # Enable fallback when MCP unavailable
    enabled: true

    # Automatically activate fallback
    auto_activate: true

    # Local ChromaDB configuration
    chromadb:
      path: ".glitchunter/chromadb"
      collection_name: "codebase"
      embedding_model: "nomic-embed-text-v1.5"
      persist: true

    # Local Repomix configuration
    repomix:
      output_path: ".glitchunter/repomix.xml"
      format: "xml"
      compress: true
      max_files: 100

    # Local graph configuration
    graph:
      backend: "networkx"
      persist_path: ".glitchunter/graph.pkl"
      tree_sitter_languages:
        - python
        - javascript
        - typescript
        - rust
        - go
```

### 2.3 Health Check

```python
# src/mcp/health_check.py

import asyncio
import aiohttp
from typing import Dict, Any


class SocratiCodeHealthCheck:
    """Performs health checks on SocratiCode MCP infrastructure."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mcp_host = config.get("server", {}).get("host", "localhost")
        self.mcp_port = config.get("server", {}).get("port", 8765)
        self.qdrant_port = 6333
        self.ollama_port = 11434

    async def check_all(self) -> Dict[str, Any]:
        """Checks health of all components."""
        results = {
            "mcp_server": await self.check_mcp_server(),
            "qdrant": await self.check_qdrant(),
            "ollama": await self.check_ollama(),
            "overall_healthy": False
        }

        results["overall_healthy"] = (
            results["mcp_server"]["healthy"] and
            results["qdrant"]["healthy"] and
            results["ollama"]["healthy"]
        )

        return results

    async def check_mcp_server(self) -> Dict[str, Any]:
        """Checks if MCP server is responding."""
        try:
            async with aiohttp.ClientSession() as session:
                # MCP servers typically use stdio, but we can check if port is open
                async with session.get(
                    f"http://{self.mcp_host}:{self.mcp_port}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return {"healthy": True, "message": "MCP server responding"}
                    else:
                        return {"healthy": False, "message": f"Status: {response.status}"}
        except Exception as e:
            return {"healthy": False, "message": str(e)}

    async def check_qdrant(self) -> Dict[str, Any]:
        """Checks if Qdrant is responding."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.mcp_host}:{self.qdrant_port}/api/v1/collections",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "healthy": True,
                            "message": "Qdrant responding",
                            "collections": len(data.get("result", []))
                        }
                    else:
                        return {"healthy": False, "message": f"Status: {response.status}"}
        except Exception as e:
            return {"healthy": False, "message": str(e)}

    async def check_ollama(self) -> Dict[str, Any]:
        """Checks if Ollama is responding."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.mcp_host}:{self.ollama_port}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m.get("name") for m in data.get("models", [])]
                        return {
                            "healthy": True,
                            "message": "Ollama responding",
                            "models": models
                        }
                    else:
                        return {"healthy": False, "message": f"Status: {response.status}"}
        except Exception as e:
            return {"healthy": False, "message": str(e)}
```

---

## 3. LangGraph Tool Integration

### 3.1 Tool Node Implementation

```python
# src/mcp/tool_adapter.py

from typing import Dict, Any, List, Optional, Callable
from langchain_core.tools import BaseTool
import asyncio


class SocratiCodeSearchTool(BaseTool):
    """LangGraph tool for SocratiCode codebase search."""

    name: str = "socratiCode_search"
    description: str = """
    Search the codebase using hybrid search (semantic + BM25).

    Args:
        query: Natural language search query (e.g., "authentication middleware")
        limit: Maximum number of results (default: 10)
        min_score: Minimum RRF score threshold (default: 0.1)
        language: Filter by language (optional)
        file_filter: Filter by file path (optional)

    Returns:
        List of search results with code chunks and metadata
    """

    def __init__(self, mcp_client: Any, fallback_manager: Any):
        super().__init__()
        self.mcp_client = mcp_client
        self.fallback_manager = fallback_manager

    async def _arun(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.1,
        language: Optional[str] = None,
        file_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Async run method for LangGraph."""
        try:
            # Try MCP first
            if self.mcp_client.mcp_available:
                results = await self.mcp_client.codebase_search(
                    query=query,
                    limit=limit,
                    min_score=min_score
                )
                return self._normalize_results(results, source="mcp")
            else:
                # Fallback to local
                results = await self.fallback_manager.search(
                    query=query,
                    limit=limit
                )
                return self._normalize_results(results, source="fallback")
        except Exception as e:
            # Emergency fallback
            return [{
                "error": str(e),
                "source": "error",
                "query": query
            }]

    def _run(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Sync run method (not used in async LangGraph)."""
        return asyncio.run(self._arun(*args, **kwargs))

    def _normalize_results(
        self,
        results: List[Dict],
        source: str
    ) -> List[Dict[str, Any]]:
        """Normalizes results to common format."""
        normalized = []

        for result in results:
            normalized.append({
                "file_path": result.get("file_path", result.get("path")),
                "content": result.get("content", result.get("snippet")),
                "score": result.get("score", result.get("relevance", 0)),
                "start_line": result.get("start_line", result.get("line")),
                "end_line": result.get("end_line"),
                "language": result.get("language"),
                "source": source,
                "symbol": result.get("symbol"),
                "context": result.get("context", "")
            })

        return sorted(normalized, key=lambda x: x["score"], reverse=True)


class SocratiCodeGraphQueryTool(BaseTool):
    """LangGraph tool for SocratiCode dependency graph query."""

    name: str = "socratiCode_graph_query"
    description: str = """
    Query the dependency graph for a specific file.

    Args:
        file_path: Relative path of the file (e.g., 'src/index.ts')

    Returns:
        Dependency information including imports, callers, and callees
    """

    def __init__(self, mcp_client: Any, fallback_manager: Any):
        super().__init__()
        self.mcp_client = mcp_client
        self.fallback_manager = fallback_manager

    async def _arun(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """Async run method for LangGraph."""
        try:
            if self.mcp_client.mcp_available:
                result = await self.mcp_client.codebase_graph_query(
                    file_path=file_path
                )
                return self._normalize_graph_result(result, source="mcp")
            else:
                result = await self.fallback_manager.graph_query(
                    file_path=file_path
                )
                return self._normalize_graph_result(result, source="fallback")
        except Exception as e:
            return {
                "error": str(e),
                "source": "error",
                "file_path": file_path
            }

    def _run(self, *args, **kwargs) -> Dict[str, Any]:
        """Sync run method."""
        return asyncio.run(self._arun(*args, **kwargs))

    def _normalize_graph_result(
        self,
        result: Dict,
        source: str
    ) -> Dict[str, Any]:
        """Normalizes graph query result."""
        return {
            "file_path": result.get("file_path"),
            "imports": result.get("imports", []),
            "dependents": result.get("dependents", []),
            "callers": result.get("callers", []),
            "callees": result.get("callees", []),
            "source": source
        }


class SocratiCodeContextSearchTool(BaseTool):
    """LangGraph tool for SocratiCode context artifact search."""

    name: str = "socratiCode_context_search"
    description: str = """
    Search context artifacts (DB schemas, API specs, infra configs).

    Args:
        query: Natural language search query
        artifact_name: Filter by artifact name (optional)
        limit: Maximum number of results (default: 10)

    Returns:
        List of context artifacts matching the query
    """

    def __init__(self, mcp_client: Any):
        super().__init__()
        self.mcp_client = mcp_client

    async def _arun(
        self,
        query: str,
        artifact_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Async run method for LangGraph."""
        try:
            if not self.mcp_client.mcp_available:
                return [{"error": "MCP not available for context search"}]

            results = await self.mcp_client.codebase_context_search(
                query=query,
                artifact_name=artifact_name,
                limit=limit
            )

            return [
                {
                    "artifact_name": r.get("artifact_name"),
                    "content": r.get("content"),
                    "score": r.get("score", 0),
                    "path": r.get("path")
                }
                for r in results
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def _run(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Sync run method."""
        return asyncio.run(self._arun(*args, **kwargs))


class SocratiCodeCircularTool(BaseTool):
    """LangGraph tool for detecting circular dependencies."""

    name: str = "socratiCode_circular"
    description: str = """
    Find circular dependencies in the codebase.

    Returns:
        List of circular dependency chains
    """

    def __init__(self, mcp_client: Any):
        super().__init__()
        self.mcp_client = mcp_client

    async def _arun(self) -> List[List[str]]:
        """Async run method for LangGraph."""
        try:
            if not self.mcp_client.mcp_available:
                return [["MCP not available"]]

            return await self.mcp_client.codebase_graph_circular()
        except Exception as e:
            return [[f"Error: {e}"]]

    def _run(self) -> List[List[str]]:
        """Sync run method."""
        return asyncio.run(self._arun())
```

### 3.2 LangGraph Integration

```python
# src/mcp/langgraph_integration.py

from typing import Dict, Any, List
from langgraph.graph import StateGraph
from .socratiCode_client import SocratiCodeClient
from .fallback_manager import FallbackManager
from .tool_adapter import (
    SocratiCodeSearchTool,
    SocratiCodeGraphQueryTool,
    SocratiCodeContextSearchTool,
    SocratiCodeCircularTool
)


class SocratiCodeIntegration:
    """Integrates SocratiCode MCP tools into LangGraph."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mcp_client = SocratiCodeClient(config.get("mcp_integration", {}))
        self.fallback_manager = FallbackManager(
            config.get("mcp_integration", {}).get("fallback", {})
        )
        self.tools = {}
        self.initialized = False

    async def initialize(self) -> None:
        """Initializes MCP connection and tools."""
        # Try to connect to MCP server
        mcp_connected = await self.mcp_client.connect()

        if not mcp_connected:
            print("MCP connection failed, activating fallback...")
            # Index codebase for fallback
            repo_path = self.config.get("repository_path", ".")
            await self.fallback_manager.index_codebase(repo_path)

        # Create tools
        self.tools = {
            "socratiCode_search": SocratiCodeSearchTool(
                self.mcp_client, self.fallback_manager
            ),
            "socratiCode_graph_query": SocratiCodeGraphQueryTool(
                self.mcp_client, self.fallback_manager
            ),
            "socratiCode_context_search": SocratiCodeContextSearchTool(
                self.mcp_client
            ),
            "socratiCode_circular": SocratiCodeCircularTool(
                self.mcp_client
            )
        }

        self.initialized = True

    def add_tools_to_graph(self, graph: StateGraph) -> None:
        """Adds SocratiCode tools to LangGraph."""
        if not self.initialized:
            raise RuntimeError("SocratiCode integration not initialized")

        for tool_name, tool in self.tools.items():
            # Add tool as a node
            graph.add_node(tool_name, create_tool_node(tool))

    def get_tools(self) -> List:
        """Returns list of available tools."""
        return list(self.tools.values())


def create_tool_node(tool: BaseTool) -> callable:
    """Creates a LangGraph node from a tool."""
    async def tool_node(state: Dict) -> Dict:
        """Executes tool and updates state."""
        # Extract tool arguments from state
        tool_args = state.get(f"{tool.name}_args", {})

        # Execute tool
        result = await tool.ainvoke(tool_args)

        # Update state with result
        return {
            f"{tool.name}_result": result,
            "mcp_source": result[0].get("source", "unknown") if isinstance(result, list) else result.get("source", "unknown")
        }

    return tool_node
```

---

## 4. SocratiCode Tools Reference

### 4.1 codebase_search

**Purpose:** Hybrid semantic + BM25 search across the codebase.

```python
# Usage Example
result = await mcp_client.codebase_search(
    query="authentication middleware",
    limit=10,
    min_score=0.1
)

# Response Format
[
    {
        "file_path": "src/auth/middleware.py",
        "content": "def authenticate(request): ...",
        "score": 0.95,
        "start_line": 45,
        "end_line": 67,
        "language": "python",
        "symbol": "authenticate",
        "context": "Full function context..."
    },
    ...
]
```

**Configuration:**
```yaml
mcp_integration:
  socratiCode:
    search:
      default_limit: 10
      min_score: 0.1
      include_linked_projects: false
```

### 4.2 codebase_graph_query

**Purpose:** Query dependency graph for a specific file.

```python
# Usage Example
result = await mcp_client.codebase_graph_query(
    file_path="src/auth/middleware.py"
)

# Response Format
{
    "file_path": "src/auth/middleware.py",
    "imports": [
        {"path": "src/auth/token.py", "symbols": ["verify_token"]},
        {"path": "src/db/user.py", "symbols": ["get_user"]}
    ],
    "dependents": [
        {"path": "src/api/routes.py", "symbols": ["auth_required"]},
        {"path": "src/websocket/handler.py", "symbols": ["ws_auth"]}
    ],
    "callers": ["api.routes.auth_required", "websocket.handler.ws_auth"],
    "callees": ["auth.token.verify_token", "db.user.get_user"]
}
```

**Configuration:**
```yaml
mcp_integration:
  socratiCode:
    graph:
      include_content: false
      max_depth: 3
      min_confidence: 0.7
      include_tests: false
```

### 4.3 codebase_context_search

**Purpose:** Search context artifacts (DB schemas, API specs, infra configs).

```python
# Usage Example
result = await mcp_client.codebase_context_search(
    query="user table schema",
    artifact_name="database-schema",
    limit=5
)

# Response Format
[
    {
        "artifact_name": "database-schema",
        "content": "CREATE TABLE users (id UUID PRIMARY KEY, ...)",
        "score": 0.92,
        "path": ".socraticode/context/database-schema.md"
    },
    ...
]
```

**Configuration:**
```yaml
mcp_integration:
  socratiCode:
    context:
      default_limit: 10
      min_score: 0.1
      artifact_filter: null
```

### 4.4 codebase_graph_circular

**Purpose:** Find circular dependencies in the codebase.

```python
# Usage Example
result = await mcp_client.codebase_graph_circular()

# Response Format
[
    ["src/auth/middleware.py", "src/auth/token.py", "src/auth/middleware.py"],
    ["src/api/routes.py", "src/api/handlers.py", "src/api/routes.py"]
]
```

---

## 5. Fallback Strategy

### 5.1 Fallback Manager Implementation

```python
# src/mcp/fallback_manager.py

from typing import List, Dict, Any, Optional
import asyncio
import os


class FallbackManager:
    """Manages fallback infrastructure when MCP is unavailable."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chromadb = None
        self.repomix = None
        self.graph = None
        self.indexed = False
        # Lazy initialization
        self._init_lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        """Ensures fallback infrastructure is initialized."""
        async with self._init_lock:
            if self.indexed:
                return

            from .local_chromadb import LocalChromaDB
            from .local_repomix import LocalRepomix
            from .local_graph import LocalNetworkXGraph

            self.chromadb = LocalChromaDB(self.config.get("chromadb", {}))
            self.repomix = LocalRepomix(self.config.get("repomix", {}))
            self.graph = LocalNetworkXGraph(self.config.get("graph", {}))

    async def index_codebase(self, repo_path: str) -> None:
        """Indexes codebase for fallback search."""
        await self._ensure_initialized()

        # 1. Generate embeddings with local model
        await self.chromadb.index_directory(repo_path)

        # 2. Build dependency graph with Tree-sitter
        await self.graph.build_from_directory(repo_path)

        # 3. Generate Repomix XML for context
        await self.repomix.generate_xml(repo_path)

        self.indexed = True

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fallback search using local infrastructure."""
        await self._ensure_initialized()

        if not self.indexed:
            raise RuntimeError("Fallback infrastructure not indexed")

        # 1. Semantic search via ChromaDB
        semantic_results = await self.chromadb.search(query, limit=limit)

        # 2. Keyword search (BM25 approximation)
        keyword_results = await self.chromadb.keyword_search(query, limit=limit)

        # 3. Combine results (RRF-like fusion)
        combined = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            k=60
        )

        return combined[:limit]

    async def graph_query(self, file_path: str) -> Dict[str, Any]:
        """Fallback graph query using local NetworkX."""
        await self._ensure_initialized()

        if not self.indexed:
            raise RuntimeError("Fallback infrastructure not indexed")

        return self.graph.query_file(file_path)

    def _reciprocal_rank_fusion(
        self,
        *result_lists: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """Implements Reciprocal Rank Fusion for result combination."""
        scores: Dict[str, float] = {}

        for results in result_lists:
            for rank, result in enumerate(results):
                doc_id = result.get("id", result.get("file_path"))
                if doc_id:
                    scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

        # Sort by fused score
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {"id": doc_id, "score": score}
            for doc_id, score in sorted_results
        ]
```

### 5.2 Local ChromaDB

```python
# src/mcp/local_chromadb.py

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings


class LocalChromaDB:
    """Local ChromaDB for fallback vector search."""

    def __init__(self, config: Dict[str, Any]):
        self.path = config.get("path", ".glitchunter/chromadb")
        self.collection_name = config.get("collection_name", "codebase")
        self.embedding_model = config.get("embedding_model", "nomic-embed-text-v1.5")

        # Initialize client
        self.client = chromadb.PersistentClient(
            path=self.path,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = None

    async def initialize(self) -> None:
        """Initializes ChromaDB collection."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    async def index_directory(self, repo_path: str) -> None:
        """Indexes all code files in a directory."""
        if self.collection is None:
            await self.initialize()

        # Walk directory and index files
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common exclusions
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]

            for file in files:
                if self._is_code_file(file):
                    file_path = os.path.join(root, file)
                    await self._index_file(file_path, repo_path)

    async def _index_file(self, file_path: str, repo_path: str) -> None:
        """Indexes a single file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Chunk content
        chunks = self._chunk_content(content, chunk_size=512, overlap=50)

        # Generate embeddings (using local model)
        embeddings = await self._generate_embeddings([c["text"] for c in chunks])

        # Add to collection
        self.collection.add(
            documents=[c["text"] for c in chunks],
            embeddings=embeddings,
            ids=[f"{file_path}:{i}" for i in range(len(chunks))],
            metadatas=[
                {
                    "file_path": file_path,
                    "relative_path": os.path.relpath(file_path, repo_path),
                    "start_line": c["start_line"],
                    "end_line": c["end_line"],
                    "language": self._detect_language(file_path)
                }
                for c in chunks
            ]
        )

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Searches for similar code."""
        if self.collection is None:
            await self.initialize()

        # Generate query embedding
        query_embedding = await self._generate_embeddings([query])

        # Query collection
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted = []
        for i, doc in enumerate(results["documents"][0]):
            formatted.append({
                "content": doc,
                "file_path": results["metadatas"][0][i]["file_path"],
                "start_line": results["metadatas"][0][i]["start_line"],
                "end_line": results["metadatas"][0][i]["end_line"],
                "language": results["metadatas"][0][i]["language"],
                "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                "source": "fallback_chromadb"
            })

        return formatted

    def _chunk_content(
        self,
        content: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Dict]:
        """Chunks content into overlapping segments."""
        chunks = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = '\n'.join(chunk_lines)

            chunks.append({
                "text": chunk_text,
                "start_line": i,
                "end_line": i + len(chunk_lines)
            })

            i += chunk_size - overlap

        return chunks

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings using local model."""
        # Use sentence-transformers as fallback
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5')
        embeddings = model.encode(texts, convert_to_numpy=True)

        return embeddings.tolist()

    def _is_code_file(self, filename: str) -> bool:
        """Checks if file is a code file."""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
            '.php', '.swift', '.kt', '.scala', '.r', '.sql'
        }
        _, ext = os.path.splitext(filename)
        return ext.lower() in code_extensions

    def _detect_language(self, file_path: str) -> str:
        """Detects language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql'
        }
        _, ext = os.path.splitext(file_path)
        return ext_map.get(ext.lower(), 'unknown')
```

---

## 6. Hardware-Specific Configuration

### 6.1 Stack A (GTX 3060, 8GB)

```yaml
# config.stack_a.yaml - MCP Section

mcp_integration:
  enabled: false  # Disabled on Stack A (resource constraints)

  # Use fallback only
  fallback:
    enabled: true
    auto_activate: true

    chromadb:
      path: ".glitchunter/chromadb_lite"
      collection_name: "codebase"
      embedding_model: "nomic-embed-text-v1.5"

    repomix:
      output_path: ".glitchunter/repomix.xml"
      format: "xml"
      max_files: 50  # Reduced for memory constraints

    graph:
      backend: "networkx"
      persist_path: ".glitchunter/graph.pkl"
      tree_sitter_languages:
        - python
        - javascript
        - typescript
```

### 6.2 Stack B (RTX 3090, 24GB)

```yaml
# config.stack_b.yaml - MCP Section

mcp_integration:
  enabled: true

  server:
    host: localhost
    port: 8765
    timeout_seconds: 30

  socratiCode:
    enabled: true
    auto_index: true
    index_on_start: false
    poll_interval_seconds: 60

    tools:
      - codebase_search
      - codebase_graph_query
      - codebase_context_search
      - codebase_graph_circular

    search:
      default_limit: 10
      min_score: 0.1
      include_linked_projects: true

    graph:
      include_content: false
      max_depth: 5
      min_confidence: 0.7

  fallback:
    enabled: true  # Keep as backup
    auto_activate: true

    chromadb:
      path: ".glitchunter/chromadb"
      collection_name: "codebase"
      embedding_model: "nomic-embed-text-v1.5"

    repomix:
      output_path: ".glitchunter/repomix.xml"
      format: "xml"
      max_files: 100

    graph:
      backend: "networkx"
      persist_path: ".glitchunter/graph.pkl"
      tree_sitter_languages:
        - python
        - javascript
        - typescript
        - rust
        - go
        - java
        - cpp
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/unit/test_mcp/test_socratiCode_client.py

import pytest
from glitchhunter.mcp.socratiCode_client import SocratiCodeClient


class TestSocratiCodeClient:
    """Unit tests for SocratiCode MCP client."""

    @pytest.fixture
    async def client(self, config):
        c = SocratiCodeClient(config["mcp"])
        await c.connect()
        return c

    @pytest.mark.asyncio
    async def test_codebase_search(self, client):
        """Tests hybrid search functionality."""
        results = await client.codebase_search(
            query="authentication middleware",
            limit=10
        )

        assert len(results) > 0
        assert all("content" in r for r in results)
        assert all("file_path" in r for r in results)

    @pytest.mark.asyncio
    async def test_graph_query(self, client):
        """Tests dependency graph query."""
        result = await client.codebase_graph_query(
            file_path="src/auth/middleware.py"
        )

        assert "imports" in result
        assert "dependents" in result

    @pytest.mark.asyncio
    async def test_context_search(self, client):
        """Tests context artifact search."""
        results = await client.codebase_context_search(
            query="user table schema",
            artifact_name="database-schema"
        )

        assert len(results) > 0
        assert all("artifact_name" in r for r in results)

    @pytest.mark.asyncio
    async def test_circular_detection(self, client):
        """Tests circular dependency detection."""
        result = await client.codebase_graph_circular()

        assert isinstance(result, list)
        # Each circular dependency is a list of file paths
        for cycle in result:
            assert isinstance(cycle, list)
            assert len(cycle) >= 2

    @pytest.mark.asyncio
    async def test_fallback_activation(self, config):
        """Tests fallback activation when MCP unavailable."""
        config["mcp"]["server"]["port"] = 9999  # Invalid port

        client = SocratiCodeClient(config["mcp"])
        connected = await client.connect()

        assert connected is False
        assert client.mcp_available is False
```

### 7.2 Integration Tests

```python
# tests/integration/test_mcp/test_langgraph_integration.py

import pytest
from glitchhunter.mcp.langgraph_integration import SocratiCodeIntegration
from glitchhunter.state.state_machine import GlitchHunterState


class TestLangGraphIntegration:
    """Integration tests for LangGraph + SocratiCode."""

    @pytest.fixture
    async def integration(self, config):
        integration = SocratiCodeIntegration(config)
        await integration.initialize()
        return integration

    @pytest.mark.asyncio
    async def test_tool_execution(self, integration):
        """Tests tool execution in LangGraph context."""
        tools = integration.get_tools()

        assert len(tools) >= 4

        # Test search tool
        search_tool = next(t for t in tools if t.name == "socratiCode_search")
        results = await search_tool.ainvoke({
            "query": "authentication middleware"
        })

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_state_update(self, integration):
        """Tests state update after tool execution."""
        # Create initial state
        state: GlitchHunterState = {
            "repository_path": "/test/repo",
            "started_at": "2024-01-01T00:00:00Z",
            "config": {}
        }

        # Execute search tool
        search_tool = integration.tools["socratiCode_search"]
        tool_node = create_tool_node(search_tool)

        state["socratiCode_search_args"] = {
            "query": "authentication middleware",
            "limit": 5
        }

        result = await tool_node(state)

        assert "socratiCode_search_result" in result
        assert len(result["socratiCode_search_result"]) > 0

    @pytest.mark.asyncio
    async def test_fallback_in_graph(self, config):
        """Tests fallback activation within LangGraph."""
        # Configure invalid MCP server
        config["mcp"]["server"]["port"] = 9999

        integration = SocratiCodeIntegration(config)
        await integration.initialize()

        # Tools should still work via fallback
        search_tool = integration.tools["socratiCode_search"]
        results = await search_tool.ainvoke({
            "query": "test query"
        })

        # Results should come from fallback
        assert len(results) > 0
        assert all(r.get("source") == "fallback" for r in results)
```

### 7.3 End-to-End Tests

```python
# tests/e2e/test_mcp/test_full_pipeline.py

import pytest
from glitchhunter.main import GlitchHunter


class TestMCPFullPipeline:
    """End-to-end tests for MCP integration in full pipeline."""

    @pytest.fixture
    async def glitchhunter(self, config):
        gh = GlitchHunter(config)
        await gh.initialize()
        return gh

    @pytest.mark.asyncio
    async def test_phase1_with_mcp(self, glitchhunter, sample_repo):
        """Tests Phase 1 ingestion with MCP integration."""
        result = await glitchhunter.analyze(sample_repo)

        # Verify MCP was used
        assert "mcp_context" in result["phase1"]
        mcp_context = result["phase1"]["mcp_context"]

        # Verify search results
        if mcp_context.get("source") == "mcp":
            assert "search_results" in mcp_context
            assert len(mcp_context["search_results"]) > 0

    @pytest.mark.asyncio
    async def test_phase2_with_graph_query(self, glitchhunter, sample_repo):
        """Tests Phase 2 with graph query integration."""
        result = await glitchhunter.analyze(sample_repo)

        # Verify graph data is available
        phase2 = result["phase2"]
        assert "data_flow_graph" in phase2
        assert "control_flow_graph" in phase2

    @pytest.mark.asyncio
    async def test_fallback_full_pipeline(self, config, sample_repo):
        """Tests full pipeline with fallback activated."""
        # Configure invalid MCP
        config["mcp"]["server"]["port"] = 9999

        gh = GlitchHunter(config)
        await gh.initialize()

        # Pipeline should still work with fallback
        result = await gh.analyze(sample_repo)

        # Verify fallback was used
        assert result["phase1"]["mcp_context"]["source"] == "fallback"

        # Pipeline should complete successfully
        assert "phase2" in result
        assert "phase3" in result
```

---

## Appendix A: Troubleshooting

### A.1 Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| MCP connection timeout | `ConnectionError: Timeout` | Check if SocratiCode server is running: `ps aux | grep socratiCode` |
| Qdrant not responding | `Qdrant health check failed` | Restart Qdrant container: `docker restart qdrant_socratiCode` |
| Ollama model missing | `Model not found: nomic-embed-text` | Pull model: `ollama pull nomic-embed-text` |
| Indexing stuck | Index progress not advancing | Check disk space and memory |
| Fallback not activating | `MCP not available` errors | Verify fallback config is enabled |

### A.2 Debug Commands

```bash
# Check MCP server status
curl -s http://localhost:8765/health

# Check Qdrant status
curl -s http://localhost:6333/api/v1/collections

# Check Ollama models
ollama list

# View SocratiCode logs
journalctl -u socratiCode-mcp -f

# Restart all services
docker restart qdrant_socratiCode
systemctl restart socratiCode-mcp
ollama serve  # In separate terminal
```

---

**END OF DOCUMENT**