# Architecture: How Kusto AI Assistant Works

## Overview

Kusto AI Assistant uses the **Model Context Protocol (MCP)** to bridge
GitHub Copilot and Azure Data Explorer (Kusto). MCP is an open standard
that lets AI assistants use external tools - in our case, tools that
query Kusto clusters.

## Data Flow

```
  User (natural language)
       |
       v
  GitHub Copilot (LLM)
       |
       | MCP Protocol (stdio)
       v
  Kusto AI Assistant (MCP Server)
       |
       | Azure SDK + AAD Auth
       v
  Azure Data Explorer (Kusto)
       |
       v
  Query Results
       |
       | MCP Protocol
       v
  GitHub Copilot (LLM)
       |
       v
  Human-readable answer
```

## Components

### 1. MCP Server (`mcp_server.py`)
A Python process that runs locally and exposes three tools via MCP:
- **`execute_kql`** - Run any KQL query
- **`get_table_schema`** - Inspect table structure
- **`list_tables`** - Discover available tables

### 2. Configuration (`config/config.json`)
Defines which Kusto clusters the server can connect to. Supports
environment variable substitution (`${VAR_NAME}`) so secrets stay
in `.env` files, never in code.

### 3. Authentication (`pre_auth.py`)
Uses Azure Identity SDK to authenticate via browser or device code.
Credentials are cached locally so the MCP server can start without
interactive prompts.

### 4. Copilot Custom Instructions (`prompts/kusto-context.md`)
Optional file that teaches Copilot KQL syntax and best practices.
When loaded as a custom instruction in VS Code, it improves query
quality significantly.

## How the LLM generates KQL

1. User asks: *"How many ADLS backup customers are there?"*
2. Copilot reads the custom instructions (KQL patterns, best practices)
3. Copilot calls `list_tables` to see available tables
4. Copilot calls `get_table_schema` on relevant tables
5. Copilot writes a KQL query based on the schema
6. Copilot calls `execute_kql` with the generated query
7. Copilot interprets the results and responds in English

The LLM handles the NL-to-KQL translation. The MCP server handles
authentication and query execution. This separation means:
- No KQL knowledge needed by the PM
- No custom NL-to-KQL model to train
- Works with any Kusto cluster immediately

## Security

- Credentials are cached locally (Azure Identity token cache)
- No secrets in config files (env var substitution)
- MCP communicates via local stdio (no network exposure)
- Queries run with the user's own AAD permissions
- The server adds `| limit N` to prevent runaway queries

## Requirements

- Python 3.10+
- VS Code with GitHub Copilot (Agent Mode)
- Azure CLI (`az login`) or browser auth
- Network access to Kusto cluster endpoints
