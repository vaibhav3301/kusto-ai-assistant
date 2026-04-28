# Azure Backup - Data Context

You are helping a PM analyze Azure Backup telemetry data.

## Clusters

| Name | URL | Database |
|------|-----|----------|
| backup-prod1 | https://mabprod1.kusto.windows.net/ | MABKustoProd1 |
| backup-weu | https://mabprodweu.kusto.windows.net/ | MABKustoProd |
| backup-wus | https://mabprodwus.kusto.windows.net/ | MABKustoProd |

## Key Table: AddonAzureBackupJobsDPP

This is the main table for backup job telemetry. **Important:** The actual
data is stored inside a JSON column called `properties`. You MUST use
`parse_json(properties)` to extract fields.

### How to query this table

```kql
AddonAzureBackupJobsDPP
| where TIMESTAMP > ago(7d)
| extend props = parse_json(properties)
| extend
    DatasourceType = tostring(props.DatasourceType),
    JobOperation = tostring(props.JobOperation),
    JobStatus = tostring(props.JobStatus),
    SubscriptionId = tostring(props.SubscriptionId),
    VaultName = tostring(props.VaultName),
    AzureDataCenter = tostring(props.AzureDataCenter)
```

### DatasourceType values (what's being backed up)

| DatasourceType | What it is |
|---------------|------------|
| Microsoft.Compute/disks | Azure Managed Disks |
| Microsoft.Storage/storageAccounts/blobServices | Azure Blob Storage |
| Microsoft.Storage/storageAccounts/adlsBlobServices | Azure Data Lake Storage (ADLS) |
| Microsoft.ContainerService/managedClusters | Azure Kubernetes Service (AKS) |
| Microsoft.ElasticSan/elasticSans/volumeGroups | Azure Elastic SAN |
| Microsoft.DBforPostgreSQL/flexibleServers | PostgreSQL Flexible Server |
| Microsoft.DBforPostgreSQL/servers/databases | PostgreSQL Single Server |

### JobOperation values
- `Backup` - A backup job
- `Restore` - A restore job

### JobStatus values
- `Completed` - Job succeeded
- `Failed` - Job failed
- `InProgress` - Job is still running

## Other Useful Tables

| Table | What it has |
|-------|------------|
| CoreAzureBackupDPP | Backup item/policy configuration data (also JSON properties) |
| CWESVaultedBackupStats | Vaulted backup stats with direct columns (no JSON parsing needed) |
| DppBlobWorkloadSubscriptionUsageStats | Blob backup usage per subscription |

## Tips

- Always add a time filter: `where TIMESTAMP > ago(7d)`
- For customer count, use: `dcount(tostring(props.SubscriptionId))`
- For regional breakdown, group by: `tostring(props.AzureDataCenter)`
- To exclude test/BVT data, filter out vault names containing "Test" or "BVT"
