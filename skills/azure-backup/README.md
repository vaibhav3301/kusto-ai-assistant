# Skill: Azure Backup

This skill teaches the Kusto AI Assistant about Azure Backup telemetry.

## What's included

| File | What it does |
|------|-------------|
| `context.md` | Tells the assistant which tables exist, what columns mean, and how the data is structured |
| `sample-questions.md` | Example questions you can ask, so you know what's possible |
| `clusters.md` | Which Kusto clusters to connect to for Backup data |

## How to use

1. When chatting with Copilot, you can reference this skill:
   > "Using the Azure Backup skill, how many ADLS customers do we have?"

2. Or load `context.md` as a custom instruction (see main README)

## Sample questions you can ask

- "How many subscriptions are using ADLS backup?"
- "What's the backup success rate this week?"
- "Show me the top 10 vaults with the most failures"
- "Which regions have the most backup customers?"
- "What types of workloads are being backed up?"
