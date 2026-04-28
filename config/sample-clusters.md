# Sample Cluster Configurations

Below are example configurations for different Microsoft teams. Copy the relevant
section into your `config/config.json` and set the corresponding environment
variables in your `.env` file.

---

## Azure Backup PM

```json
{
  "clusters": {
    "backup-prod1": {
      "url": "${KUSTO_BACKUP_MABPROD1_URL}",
      "database": "${KUSTO_BACKUP_MABPROD1_DB}"
    },
    "backup-weu": {
      "url": "${KUSTO_BACKUP_MABPRODWEU_URL}",
      "database": "${KUSTO_BACKUP_MABPRODWEU_DB}"
    },
    "backup-wus": {
      "url": "${KUSTO_BACKUP_MABPRODWUS_URL}",
      "database": "${KUSTO_BACKUP_MABPRODWUS_DB}"
    }
  }
}
```

**.env**
```
KUSTO_BACKUP_MABPROD1_URL=https://mabprod1.kusto.windows.net/
KUSTO_BACKUP_MABPROD1_DB=MABKustoProd1
KUSTO_BACKUP_MABPRODWEU_URL=https://mabprodweu.kusto.windows.net/
KUSTO_BACKUP_MABPRODWEU_DB=MABKustoProd
KUSTO_BACKUP_MABPRODWUS_URL=https://mabprodwus.kusto.windows.net/
KUSTO_BACKUP_MABPRODWUS_DB=MABKustoProd
```

---

## Azure Storage PM

```json
{
  "clusters": {
    "xstore": {
      "url": "${KUSTO_XSTORE_URL}",
      "database": "${KUSTO_XSTORE_DB}"
    },
    "xstorepm": {
      "url": "${KUSTO_XSTOREPM_URL}",
      "database": "${KUSTO_XSTOREPM_DB}"
    },
    "xdataanalytics": {
      "url": "${KUSTO_XDATAANALYTICS_URL}",
      "database": "${KUSTO_XDATAANALYTICS_DB}"
    }
  }
}
```

**.env**
```
KUSTO_XSTORE_URL=https://xstore.kusto.windows.net/
KUSTO_XSTORE_DB=xstore
KUSTO_XSTOREPM_URL=https://xstorepm.westcentralus.kusto.windows.net/
KUSTO_XSTOREPM_DB=XStorePM
KUSTO_XDATAANALYTICS_URL=https://xdataanalytics.westcentralus.kusto.windows.net/
KUSTO_XDATAANALYTICS_DB=XDataAnalytics
```

---

## Generic / Getting Started (Public Samples)

No `.env` needed. The server defaults to the public samples cluster if nothing is configured.

```json
{
  "clusters": {
    "samples": {
      "url": "https://help.kusto.windows.net",
      "database": "Samples"
    }
  }
}
```

---

## Multi-Team Config

You can combine clusters from different teams:

```json
{
  "clusters": {
    "backup-prod1": { "url": "...", "database": "..." },
    "xstore": { "url": "...", "database": "..." },
    "azurecm": { "url": "https://azurecm.kusto.windows.net/", "database": "AzureCM" }
  }
}
```

The MCP server will expose all clusters to Copilot, so you can ask questions across
any of them in a single chat session.
