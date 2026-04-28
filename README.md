# Kusto AI Assistant

> **Ask questions about your data in plain English. Get answers instantly.**

No KQL knowledge needed. No coding required. Just ask.

```
You:     "How many backup customers do we have this week?"
Copilot: "There are 3,187 unique subscriptions with active backup jobs
          across 58 regions. Top regions: Canada Central (847),
          Australia East (623), UAE North (412)..."
```

---

## What is this?

Kusto AI Assistant connects **GitHub Copilot** (the AI in VS Code) to your
team's **Kusto telemetry data**. You ask questions in English, and it:

1. Figures out which table has the data you need
2. Writes the Kusto query for you
3. Runs it against your cluster
4. Gives you the answer in plain English

**You never write a single line of KQL.**

---

## What are Skills?

**Skills** are knowledge packs that teach the assistant about your team's
specific data. Each skill contains:

| File | What it does |
|------|-------------|
| `context.md` | Describes your tables, columns, and data patterns so the AI knows how to query them |
| `sample-questions.md` | Example questions you can ask — great for learning what's possible |
| `README.md` | Overview of the skill |

### Available Skills

| Skill | For | What you can ask |
|-------|-----|-----------------|
| [Azure Backup](skills/azure-backup/) | Backup & BCDR PMs | Customer counts, failure rates, job trends, regional breakdowns |
| [Azure Storage](skills/azure-storage/) | Storage PMs | Account capacity, transactions, security audit, critical customers |

### Creating Your Own Skill

Any PM can create a skill for their team's data. It's just writing a few
markdown files - no code:

1. Copy the [`skills/_template/`](skills/_template/) folder
2. Rename it to your team name (e.g., `skills/my-team/`)
3. Edit `context.md` — describe your Kusto tables and what the columns mean
4. Edit `sample-questions.md` — add questions your team commonly asks
5. Share it with your team!

See the [template README](skills/_template/README.md) for detailed guidance.

---

## Setup Guide (Step by Step)

### What you need before starting

- [x] **VS Code** — [Download here](https://code.visualstudio.com/) if you don't have it
- [x] **GitHub Copilot** — You should already have this through Microsoft (check Extensions in VS Code)
- [x] **Python** — [Download Python 3.12+](https://www.python.org/downloads/) → during install, **check "Add to PATH"**
- [x] **Access to a Kusto cluster** — If you can open your data in Azure Data Explorer web, you have access

### Step 1: Download this project

**Option A — If you have Git:**
Open a terminal (PowerShell or Command Prompt) and run:
```
git clone https://github.com/vaibhav3301/kusto-ai-assistant.git
cd kusto-ai-assistant
```

**Option B — If you don't have Git:**
1. Go to https://github.com/vaibhav3301/kusto-ai-assistant
2. Click the green **"Code"** button → **"Download ZIP"**
3. Extract the ZIP to a folder (e.g., `C:\Users\YourName\kusto-ai-assistant`)
4. Open a terminal and `cd` into that folder

### Step 2: Run the setup

```
python setup.py
```

This will:
- Create an isolated Python environment (won't affect anything else on your machine)
- Install the required packages
- Open a browser window for you to sign in with your Microsoft account

**Sign in with your work account** (the same one you use for Azure/Kusto).

### Step 3: Add your Kusto cluster

1. In the project folder, go to `config/`
2. Copy `config.json.template` and rename the copy to `config.json`
3. Open `config.json` in any text editor (even Notepad)
4. Replace the placeholder with your cluster URL:

```json
{
  "clusters": {
    "my-data": {
      "url": "https://your-cluster.kusto.windows.net/",
      "database": "YourDatabaseName"
    }
  }
}
```

**Don't know your cluster URL?** It's the URL in your browser when you open
Azure Data Explorer. Or ask your engineering team. Or check
[`config/sample-clusters.md`](config/sample-clusters.md) for common Microsoft
cluster configs.

**Want multiple clusters?** Just add more entries:
```json
{
  "clusters": {
    "backup-data": {
      "url": "https://mabprod1.kusto.windows.net/",
      "database": "MABKustoProd1"
    },
    "storage-data": {
      "url": "https://xstorepm.westcentralus.kusto.windows.net/",
      "database": "XStorePM"
    }
  }
}
```

### Step 4: Connect it to VS Code

1. Open **VS Code**
2. Press `Ctrl+Shift+P` (opens the Command Palette)
3. Type **"MCP"** and select **"MCP: Open User Configuration"**
4. This opens a JSON file. Add the following (replace the path with where you put the project):

```json
{
  "servers": {
    "kusto-ai-assistant": {
      "command": "C:\\Users\\YourName\\kusto-ai-assistant\\venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\YourName\\kusto-ai-assistant\\mcp_server.py"
      ],
      "env": {
        "KUSTO_CONFIG_FILE": "C:\\Users\\YourName\\kusto-ai-assistant\\config\\config.json"
      }
    }
  }
}
```

5. Save the file
6. You should see a **"Start"** button appear next to the server name — click it
7. It should show **"Running"** ✓

### Step 5: Load a skill (recommended)

1. Press `Ctrl+Shift+P` → type **"Custom Instructions"** → select **"Copilot: Configure Custom Instructions"**
2. Add the path to the skill context file for your team:
   - Backup PMs: `C:\Users\YourName\kusto-ai-assistant\skills\azure-backup\context.md`
   - Storage PMs: `C:\Users\YourName\kusto-ai-assistant\skills\azure-storage\context.md`
   - General: `C:\Users\YourName\kusto-ai-assistant\prompts\kusto-context.md`

This teaches Copilot about your specific data, so it writes better queries.

### Step 6: Start asking questions!

1. Open **GitHub Copilot Chat** (click the Copilot icon in the sidebar, or `Ctrl+Shift+I`)
2. Make sure **Agent Mode** is enabled (toggle at the top of the chat)
3. Ask away:

```
"List all tables in my database"
"How many customers are using backup this week?"
"What's the failure rate trend for the last 30 days?"
"Show me the top regions by activity"
```

---

## How it looks in practice

**You type:**
> "How many unique subscriptions are using ADLS backup in the last 5 days?"

**Copilot does (behind the scenes):**
1. Reads the skill context to understand the data
2. Calls `list_tables` to see what's available
3. Calls `get_table_schema` on the relevant table
4. Generates a KQL query with `parse_json(properties)` and `dcount()`
5. Runs the query via `execute_kql`
6. Summarizes: *"100 unique subscriptions across 289 vaults in 48 regions,
   with an 83% success rate"*

**Total time: ~30 seconds** (vs. 15-30 minutes writing KQL manually)

---

## FAQ

**Q: I don't know KQL. Can I still use this?**
Yes! That's the whole point. Ask in plain English.

**Q: What if it gives me wrong data?**
Ask it to double-check: *"Are you sure? Show me the query you used."*
You can also say *"Try a different approach"* or give hints.

**Q: Is my data safe?**
Yes. Everything runs on your machine. The AI can only access clusters you
configured with your own credentials.

**Q: The server won't start. What do I do?**
Run `python pre_auth.py` again to refresh your authentication. Make sure
you can access your Kusto cluster in a browser first.

**Q: Can I share my skills with my team?**
Absolutely! That's the point. Create a skill, commit it to the repo, and
share. Each team member just needs to set up the project once.

**Q: I want to add my team's data. How?**
Copy `skills/_template/`, fill in your tables and columns, and you're done.
See the [template guide](skills/_template/README.md).

---

## Project Structure

```
kusto-ai-assistant/
├── mcp_server.py                 # The engine (you don't need to touch this)
├── pre_auth.py                   # Sign-in helper
├── setup.py                      # One-command setup
├── requirements.txt              # Python packages (handled by setup.py)
├── config/
│   ├── config.json.template      # Your cluster config (copy and edit)
│   └── sample-clusters.md        # Example configs for common clusters
├── skills/                       # ⭐ SKILLS - domain knowledge packs
│   ├── azure-backup/             # Backup PM skill
│   │   ├── context.md            #   Table/column descriptions
│   │   └── sample-questions.md   #   Example questions
│   ├── azure-storage/            # Storage PM skill
│   │   ├── context.md
│   │   └── sample-questions.md
│   └── _template/                # Copy this to create your own skill
│       ├── README.md
│       ├── context.md
│       └── sample-questions.md
├── prompts/
│   └── kusto-context.md          # General KQL knowledge (for any team)
├── examples/                     # Detailed NL→KQL examples
│   ├── backup-queries.md
│   ├── storage-queries.md
│   └── general-queries.md
└── docs/
    └── architecture.md           # Technical details (optional reading)
```

---

## Contributing

1. **Create a skill for your team** — Copy `skills/_template/` and fill it in
2. **Add sample questions** — Help others learn what's possible
3. **Share this repo** — The more PMs use it, the more skills we build

---

## License

MIT — See [LICENSE](LICENSE)
