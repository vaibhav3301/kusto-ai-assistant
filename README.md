# Kusto AI Assistant

> **Talk to your telemetry.** Ask questions in plain English, get answers from Kusto.

Kusto AI Assistant is an MCP (Model Context Protocol) server that connects
GitHub Copilot in VS Code directly to your Azure Data Explorer (Kusto)
clusters. No KQL expertise needed - just ask your question and get results.

## The Problem

PMs spend hours writing complex KQL queries to answer simple questions like
*"How many backup customers do we have?"* or *"What's the failure rate this week?"*
This requires deep Kusto expertise and knowledge of table schemas.

## The Solution

```
You:     "Show me ADLS backup failures in the last 7 days by region"
Copilot: [generates KQL → executes → returns formatted results]
         "There were 342 failures across 12 regions. UAE North had the most
          with 65 failures (19%), followed by Central India with 48 (14%)..."
```

The LLM handles the translation. The MCP server handles authentication and
execution. You just ask questions.

---

## Quick Start (5 minutes)

### Prerequisites
- Python 3.10+
- VS Code with GitHub Copilot
- Access to a Kusto cluster (or use the free public Samples cluster)

### 1. Clone and Setup

```bash
git clone https://github.com/vaibhav3301/kusto-ai-assistant.git
cd kusto-ai-assistant
python setup.py
```

This creates a virtual environment, installs dependencies, and walks you
through authentication.

### 2. Configure Your Clusters

```bash
# Copy the template
cp config/config.json.template config/config.json
```

Edit `config/config.json` with your cluster URLs. See
[`config/sample-clusters.md`](config/sample-clusters.md) for team-specific
examples.

Create a `.env` file with your cluster details:
```
KUSTO_CLUSTER_URL=https://your-cluster.kusto.windows.net/
KUSTO_DATABASE=YourDatabase
```

### 3. Configure VS Code

1. Open VS Code
2. `Ctrl+Shift+P` → **"MCP: Open User Configuration"**
3. Add this server (update paths):

```json
{
  "servers": {
    "kusto-ai-assistant": {
      "command": "C:/path/to/kusto-ai-assistant/venv/Scripts/python.exe",
      "args": ["C:/path/to/kusto-ai-assistant/mcp_server.py"],
      "env": {
        "KUSTO_CONFIG_FILE": "C:/path/to/kusto-ai-assistant/config/config.json"
      }
    }
  }
}
```

4. Click **Start** on the server in MCP settings
5. Open Copilot Chat → Enable **Agent Mode**

### 4. Start Asking Questions!

```
"List all tables in my database"
"What columns does the AddonAzureBackupJobsDPP table have?"
"How many unique subscriptions ran backup jobs this week?"
"Show me the daily failure trend for the last 30 days"
"Which regions have the most customers?"
```

---

## How It Works

```
  You (plain English)
       │
       ▼
  GitHub Copilot ◄──── Custom Instructions (KQL patterns)
       │
       │ MCP Protocol
       ▼
  Kusto AI Assistant (this server)
       │
       │ Azure SDK + Your Credentials
       ▼
  Azure Data Explorer
       │
       ▼
  Results → Copilot → Plain English Answer
```

See [`docs/architecture.md`](docs/architecture.md) for details.

---

## Available Tools

| Tool | Description |
|------|-------------|
| `execute_kql` | Run any KQL query against a configured cluster |
| `get_table_schema` | Get column names and types for a table |
| `list_tables` | List all tables in a database |

---

## Copilot Custom Instructions (Optional but Recommended)

Load [`prompts/kusto-context.md`](prompts/kusto-context.md) as a custom
instruction in VS Code to significantly improve query quality:

1. `Ctrl+Shift+P` → **"Copilot: Configure Custom Instructions"**
2. Add the path to `prompts/kusto-context.md`

This teaches Copilot KQL syntax, best practices, and common PM query patterns.

---

## Example Queries by Team

| Team | Examples |
|------|----------|
| Azure Backup | [`examples/backup-queries.md`](examples/backup-queries.md) |
| Azure Storage | [`examples/storage-queries.md`](examples/storage-queries.md) |
| General | [`examples/general-queries.md`](examples/general-queries.md) |

---

## Project Structure

```
kusto-ai-assistant/
├── mcp_server.py              # MCP server (main entry point)
├── pre_auth.py                # One-time authentication helper
├── setup.py                   # One-command setup script
├── requirements.txt           # Python dependencies
├── config/
│   ├── config.json.template   # Cluster config template
│   └── sample-clusters.md     # Team-specific config examples
├── prompts/
│   └── kusto-context.md       # Copilot custom instructions for KQL
├── examples/
│   ├── backup-queries.md      # NL→KQL examples for Backup PMs
│   ├── storage-queries.md     # NL→KQL examples for Storage PMs
│   └── general-queries.md     # Generic KQL patterns
├── docs/
│   └── architecture.md        # How MCP works, data flow
└── .vscode/
    └── mcp.json.template      # VS Code MCP config template
```

---

## FAQ

**Q: Do I need to know KQL?**
No. Ask in plain English. Copilot generates the KQL for you.

**Q: Can I use multiple clusters?**
Yes. Add them all to `config/config.json`. Copilot can query any of them.

**Q: Is my data secure?**
Yes. Everything runs locally. Auth uses your own AAD credentials. No data
leaves your machine except the Kusto queries (which run with your permissions).

**Q: What if Copilot generates a bad query?**
It will see the error and retry. You can also say *"try a different approach"*
or guide it with hints like *"the status column is inside the properties JSON"*.

**Q: Can I use this outside VS Code?**
The MCP server works with any MCP-compatible client. VS Code + Copilot is
the recommended setup for the best experience.

---

## Contributing

1. Fork the repo
2. Add your team's sample queries in `examples/`
3. Submit a PR

---

## License

MIT - See [LICENSE](LICENSE)
