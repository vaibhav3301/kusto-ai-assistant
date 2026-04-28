# Azure Backup - Sample Natural Language Queries

These examples show how a PM can ask questions in plain English and get
answers from Kusto telemetry, powered by the Kusto AI Assistant.

---

## Cluster Info
- **Clusters:** `backup-prod1`, `backup-weu`, `backup-wus`
- **Key tables:** `AddonAzureBackupJobsDPP`, `CoreAzureBackupDPP`,
  `CWESVaultedBackupStats`, `DppBlobWorkloadSubscriptionUsageStats`
- **Note:** Many tables store data in a JSON `properties` column.
  The assistant will use `parse_json(properties)` automatically.

---

## Example Conversations

### 1. Active customer count

**You:** "How many unique subscriptions have run ADLS backup jobs in the last 7 days?"

**What the assistant does:**
```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(7d)
| extend props = parse_json(properties)
| where tostring(props.DatasourceType) == "Microsoft.Storage/storageAccounts/adlsBlobServices"
| where tostring(props.JobOperation) == "Backup"
| summarize dcount(tostring(props.SubscriptionId))
```

---

### 2. Failure analysis

**You:** "Show me the top 10 vaults with the most failed backup jobs this week"

**What the assistant does:**
```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(7d)
| extend props = parse_json(properties)
| where tostring(props.JobStatus) == "Failed"
| where tostring(props.JobOperation) == "Backup"
| summarize FailedJobs = count() by
    VaultName = tostring(props.VaultName),
    Region = tostring(props.AzureDataCenter)
| top 10 by FailedJobs desc
```

---

### 3. Success rate trend

**You:** "What's the daily backup success rate for blob storage over the last 30 days?"

**What the assistant does:**
```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(30d)
| extend props = parse_json(properties)
| where tostring(props.DatasourceType) has "Storage"
| where tostring(props.JobOperation) == "Backup"
| summarize
    Total = count(),
    Succeeded = countif(tostring(props.JobStatus) == "Completed")
    by bin(TIMESTAMP, 1d)
| extend SuccessRate = round(100.0 * Succeeded / Total, 1)
| order by TIMESTAMP asc
```

---

### 4. Regional distribution

**You:** "Which Azure regions have the most ADLS backup customers?"

```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(7d)
| extend props = parse_json(properties)
| where tostring(props.DatasourceType) has "adlsBlobServices"
| summarize
    Subscriptions = dcount(tostring(props.SubscriptionId)),
    Vaults = dcount(tostring(props.VaultName))
    by Region = tostring(props.AzureDataCenter)
| order by Subscriptions desc
```

---

### 5. DatasourceType breakdown

**You:** "What types of workloads are being backed up and how many jobs each?"

```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(5d)
| extend DatasourceType = tostring(parse_json(properties).DatasourceType)
| where tostring(parse_json(properties).JobOperation) == "Backup"
| summarize JobCount = count() by DatasourceType
| order by JobCount desc
```

---

### 6. Large account investigation

**You:** "Find subscriptions with more than 100 backup jobs in the last 3 days
and show their success/failure split"

```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(3d)
| extend props = parse_json(properties)
| where tostring(props.JobOperation) == "Backup"
| summarize
    Total = count(),
    Succeeded = countif(tostring(props.JobStatus) == "Completed"),
    Failed = countif(tostring(props.JobStatus) == "Failed")
    by SubscriptionId = tostring(props.SubscriptionId)
| where Total > 100
| extend FailRate = round(100.0 * Failed / Total, 1)
| order by Total desc
```
