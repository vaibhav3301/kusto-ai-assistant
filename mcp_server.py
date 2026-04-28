#!/usr/bin/env python3
"""
Kusto AI Assistant - MCP Server
Connects GitHub Copilot to Azure Data Explorer (Kusto) clusters
enabling natural language querying of telemetry data.
"""

import asyncio
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from mcp.server import Server, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

# Logging setup
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "kusto-ai-assistant.log", encoding="utf-8")
    ],
)
logger = logging.getLogger(__name__)


class KustoAIAssistant:
    """MCP Server that bridges GitHub Copilot and Azure Data Explorer."""

    def __init__(self):
        self.server = Server("kusto-ai-assistant")
        self.kusto_clients: Dict[str, KustoClient] = {}
        self.credential = None
        self.cluster_configs: Dict[str, dict] = {}

        self._load_configuration()
        self._initialize_auth()
        self._setup_handlers()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_configuration(self):
        """Load cluster configs from config.json with ${ENV_VAR} substitution."""
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info("Loaded .env file")
            except ImportError:
                logger.warning("python-dotenv not installed; skipping .env")

        config_file = os.getenv("KUSTO_CONFIG_FILE")
        if not config_file:
            candidates = [
                Path(__file__).parent / "config" / "config.json",
                Path.home() / ".kusto-ai-assistant" / "config.json",
            ]
            for p in candidates:
                if p.exists():
                    config_file = str(p)
                    break

        if config_file and os.path.exists(config_file):
            try:
                raw = Path(config_file).read_text(encoding="utf-8")
                raw = re.sub(
                    r"\$\{([^}]+)\}",
                    lambda m: os.getenv(m.group(1), m.group(0)),
                    raw,
                )
                config = json.loads(raw)
                self.cluster_configs = config.get("clusters", {})
                logger.info(f"Loaded {len(self.cluster_configs)} cluster(s) from {config_file}")
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        # Fallback: direct env vars
        url = os.getenv("KUSTO_CLUSTER_URL")
        if url and "default" not in self.cluster_configs:
            self.cluster_configs["default"] = {
                "url": url,
                "database": os.getenv("KUSTO_DATABASE", "MyDatabase"),
            }

        # Ultimate fallback: public samples cluster
        if not self.cluster_configs:
            self.cluster_configs["samples"] = {
                "url": "https://help.kusto.windows.net",
                "database": "Samples",
            }
            logger.info("No clusters configured; using public Samples cluster")

        logger.info(f"Available clusters: {list(self.cluster_configs.keys())}")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _initialize_auth(self):
        """Try cached / default credentials silently."""
        methods = [
            ("DefaultAzureCredential", lambda: DefaultAzureCredential()),
            (
                "InteractiveBrowserCredential",
                lambda: InteractiveBrowserCredential(
                    authority="https://login.microsoftonline.com/common"
                ),
            ),
        ]
        for name, factory in methods:
            try:
                cred = factory()
                cred.get_token("https://kusto.kusto.windows.net/.default")
                self.credential = cred
                logger.info(f"Authenticated via {name}")
                return
            except Exception as e:
                logger.warning(f"{name} failed: {e}")

        logger.error("All auth methods failed. Run `python pre_auth.py` first.")
        self.credential = None

    def _get_client(self, cluster_name: str) -> KustoClient:
        """Return (or create) a KustoClient for the given cluster."""
        if cluster_name not in self.kusto_clients:
            if cluster_name not in self.cluster_configs:
                available = list(self.cluster_configs.keys())
                if not available:
                    raise ValueError("No clusters configured.")
                logger.warning(f"Cluster '{cluster_name}' unknown; falling back to '{available[0]}'")
                cluster_name = available[0]

            if not self.credential:
                raise RuntimeError(
                    "Not authenticated. Run `python pre_auth.py` to sign in."
                )

            cfg = self.cluster_configs[cluster_name]
            token = self.credential.get_token("https://kusto.kusto.windows.net/.default")
            kcsb = KustoConnectionStringBuilder.with_aad_application_token_authentication(
                cfg["url"], application_token=token.token
            )
            self.kusto_clients[cluster_name] = KustoClient(kcsb)
            logger.info(f"Created client for {cluster_name} ({cfg['url']})")

        return self.kusto_clients[cluster_name]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(response) -> List[dict]:
        """Convert Kusto response to list of dicts."""
        results = []
        if response.primary_results and len(response.primary_results) > 0:
            pr = response.primary_results[0]
            cols = [c.column_name for c in pr.columns]
            for row in pr:
                results.append(
                    {col: (str(row[col]) if row[col] is not None else None) for col in cols}
                )
        return results

    # ------------------------------------------------------------------
    # MCP Handlers
    # ------------------------------------------------------------------

    def _setup_handlers(self):
        clusters = list(self.cluster_configs.keys())

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            resources = []
            for name in self.cluster_configs:
                resources.append(
                    types.Resource(
                        uri=f"kusto://{name}/tables",
                        name=f"Tables in {name}",
                        description=f"List tables in cluster {name}",
                        mimeType="application/json",
                    )
                )
            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            if not uri.startswith("kusto://"):
                raise ValueError(f"Unsupported URI: {uri}")
            parts = uri.replace("kusto://", "").split("/")
            cluster_name, resource_type = parts[0], parts[1]
            client = self._get_client(cluster_name)
            db = self.cluster_configs[cluster_name]["database"]
            if resource_type == "tables":
                query = ".show tables | project TableName"
            elif resource_type == "functions":
                query = ".show functions | project Name, Parameters"
            else:
                raise ValueError(f"Unknown resource: {resource_type}")
            resp = client.execute(db, query)
            return json.dumps(self._rows_to_dicts(resp), indent=2)

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="execute_kql",
                    description=(
                        "Execute a KQL query against a Kusto cluster. "
                        "Use this to answer data questions in natural language."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Cluster name. Available: {clusters}",
                                "default": clusters[0] if clusters else "default",
                            },
                            "database": {
                                "type": "string",
                                "description": "Database (optional; uses cluster default)",
                            },
                            "query": {
                                "type": "string",
                                "description": "KQL query to execute",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max rows (default 100, max 10000)",
                                "default": 100,
                                "maximum": 10000,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="get_table_schema",
                    description="Get column names and types for a Kusto table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Cluster name. Available: {clusters}",
                            },
                            "database": {"type": "string", "description": "Database (optional)"},
                            "table": {"type": "string", "description": "Table name"},
                        },
                        "required": ["table"],
                    },
                ),
                types.Tool(
                    name="list_tables",
                    description="List all tables in a Kusto database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Cluster name. Available: {clusters}",
                            },
                            "database": {"type": "string", "description": "Database (optional)"},
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            try:
                if name == "execute_kql":
                    return await self._tool_execute_kql(arguments)
                elif name == "get_table_schema":
                    return await self._tool_get_schema(arguments)
                elif name == "list_tables":
                    return await self._tool_list_tables(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Tool {name} error: {e}")
                return [types.TextContent(type="text", text=f"Error: {e}")]

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _tool_execute_kql(self, args: Dict[str, Any]) -> List[types.TextContent]:
        cluster = args.get("cluster", list(self.cluster_configs.keys())[0])
        db = args.get("database") or self.cluster_configs[cluster]["database"]
        query = args["query"]
        limit = args.get("limit", 100)

        if "limit" not in query.lower() and "take" not in query.lower():
            query = f"{query} | limit {limit}"

        client = self._get_client(cluster)
        logger.info(f"KQL on {cluster}/{db}: {query}")
        resp = client.execute(db, query)
        rows = self._rows_to_dicts(resp)

        text = (
            f"Cluster: {cluster} | Database: {db}\n"
            f"Rows returned: {len(rows)}\n"
            f"Query: {query}\n\n"
            f"{json.dumps(rows, indent=2, default=str)}"
        )
        return [types.TextContent(type="text", text=text)]

    async def _tool_get_schema(self, args: Dict[str, Any]) -> List[types.TextContent]:
        cluster = args.get("cluster", list(self.cluster_configs.keys())[0])
        db = args.get("database") or self.cluster_configs[cluster]["database"]
        table = args["table"]

        client = self._get_client(cluster)
        resp = client.execute(db, f".show table {table} schema as json")
        rows = self._rows_to_dicts(resp)

        text = f"Schema: {table} ({cluster}/{db})\n\n{json.dumps(rows, indent=2, default=str)}"
        return [types.TextContent(type="text", text=text)]

    async def _tool_list_tables(self, args: Dict[str, Any]) -> List[types.TextContent]:
        cluster = args.get("cluster", list(self.cluster_configs.keys())[0])
        db = args.get("database") or self.cluster_configs[cluster]["database"]

        client = self._get_client(cluster)
        resp = client.execute(db, ".show tables | project TableName")
        rows = self._rows_to_dicts(resp)

        text = f"Tables in {cluster}/{db}:\n\n{json.dumps(rows, indent=2, default=str)}"
        return [types.TextContent(type="text", text=text)]

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def run(self):
        logger.info(f"Starting Kusto AI Assistant (clusters: {list(self.cluster_configs.keys())})")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=InitializationOptions(
                    server_name="kusto-ai-assistant",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def main():
    try:
        server = KustoAIAssistant()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
