# [Your Team Name] - Data Context

You are helping a PM analyze [Your Team] telemetry data.

## Clusters

| Name | URL | Database |
|------|-----|----------|
| my-cluster | https://your-cluster.kusto.windows.net/ | YourDatabase |

## Key Tables

### TableName1
- **What it stores:** [Description]
- **Key columns:**
  - `Column1` - [What this column means]
  - `Column2` - [What this column means]
  - `Timestamp` - [Time column for filtering]

### TableName2
- **What it stores:** [Description]
- **Special notes:** [e.g., "Data is in JSON properties column"]

## Example Query

```kql
TableName1
| where Timestamp > ago(7d)
| summarize count() by Column1
| order by count_ desc
```

## Tips

- Always add a time filter to avoid scanning too much data
- [Add team-specific tips here]
