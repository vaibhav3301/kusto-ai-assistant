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

## Sample queries
//Key info
    
    //BCDR kusto clusters with prod data with blob/adls
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,  	
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where DeploymentName !in ("ccy-pod01", "ecy-pod-01", "ea-can02")
    | where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where DeploymentName !contains "-can0"
    | where Artifact_BackupProvider contains "blob" or Artifact_BackupProvider contains "adls"  // Filtering adls and blob accounts
    | extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))                     //Input Storage account 
    
    //BCDR PM sub
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,  	
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where Artifact_SubscriptionId == "ef4ab5a7-c2c0-4304-af80-af49f48af3d1"
    





// baseQuery BlobBackupStats
let BlobBackupStats = () {
    let timeduration = 2d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,  	
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where ServiceName == "backupcs" and ActivityName in ("Backup", "Restore") and ActivityType in ("ScheduledBackup", "AdhocBackup", "Restore")
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/blobServices", "Microsoft.Storage/storageAccounts/adlsBlobServices")
    | where DeploymentName !in ("ccy-pod01", "ecy-pod-01", "ea-can02")
    //| where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where DeploymentName !contains "-can0"
    | extend InputData = parse_json(Input)
    | extend ErrorDetailsData = parse_json(ErrorDetails)
    | extend DestinationDataStoreName  = tostring(InputData.DestinationDataStoreName), DestinationDataStoreId  = tostring(InputData.DestinationDataStoreId), TargetDataStore  = tostring(InputData.TargetDatastore)
    | extend ErrorCode = tostring(ErrorDetailsData.ErrorCode)
    | extend InternalErrorCode = ErrorDetailsData.ErrorDetails
    | project TIMESTAMP, ActivityName, ActivityType, DeploymentName, TaskId = Instance_TaskId, SubscriptionId = Artifact_SubscriptionId, VaultId = Artifact_VaultId, TargetDataStore,
        BackupInstanceId = Artifact_BackupInstanceId, StorageAccountId = Artifact_DataSourceId,  Result, ErrorCode, InternalErrorCode, DestinationDataStoreName, BackupProvider = Artifact_BackupProvider
};
let UserErorrs = ExpectedCloudErrors
    | where UserError == true
    | summarize by ErrorCode = Name;
BlobBackupStats
| where ActivityName == "Backup"
| extend Blob_ADLS = iff(BackupProvider contains "ADLS", "ADLS", "Blob") 
//| where BackupProvider == "Microsoft.Storage/storageAccounts/adlsBlobServices"
| where DestinationDataStoreName == "VaultStore"
| extend UserError = iff(ErrorCode contains "UserError" or ErrorCode in (UserErorrs),"y","n") 
//| where ErrorCode !contains "success"
| summarize count(), dcount(BackupInstanceId) by ErrorCode,UserError, Blob_ADLS
| sort by Blob_ADLS, count_ desc 
| where Blob_ADLS contains "ADLS"

// ADLS/Blob PIs region wise
let BlobBackupStats = () {
    let timeduration = 10d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,  	
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where ServiceName == "backupcs" and ActivityName in ("Backup", "Restore") and ActivityType in ("ScheduledBackup", "AdhocBackup", "Restore")
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/blobServices", "Microsoft.Storage/storageAccounts/adlsBlobServices")
    | where DeploymentName !in ("ccy-pod01", "ecy-pod-01", "ea-can02")
    //| where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where DeploymentName !contains "-can0"
    | extend InputData = parse_json(Input)
    | extend ErrorDetailsData = parse_json(ErrorDetails)
    | extend DestinationDataStoreName  = tostring(InputData.DestinationDataStoreName), DestinationDataStoreId  = tostring(InputData.DestinationDataStoreId), TargetDataStore  = tostring(InputData.TargetDatastore)
    | extend ErrorCode = tostring(ErrorDetailsData.ErrorCode)
    | extend InternalErrorCode = ErrorDetailsData.ErrorDetails
    | project TIMESTAMP, ActivityName, ActivityType, DeploymentName, TaskId = Instance_TaskId, SubscriptionId = Artifact_SubscriptionId, VaultId = Artifact_VaultId, TargetDataStore,
        BackupInstanceId = Artifact_BackupInstanceId, StorageAccountId = Artifact_DataSourceId,  Result, ErrorCode, InternalErrorCode, DestinationDataStoreName, BackupProvider = Artifact_BackupProvider
};
BlobBackupStats
| summarize dcount(BackupInstanceId) by DeploymentName, BackupProvider

================================================================================
QUERY 1: Overall Summary (Jobs, Success/Fail, Duration)
================================================================================

let InternalSubs = cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions();
let RunnerSubs = cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions();
let InternalBackupSubs = cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions();
union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
| where Artifact_BackupProvider contains "adls"
| where StartTime >= ago(1d)
| where ActivityName == "Backup"
| where Artifact_SubscriptionId !in (InternalSubs) 
    and Artifact_SubscriptionId !in (RunnerSubs) 
    and Artifact_SubscriptionId !in (InternalBackupSubs)
| extend DurationMin = round(datetime_diff('millisecond', EndTime, StartTime) / 60000.0, 1)
| summarize 
    TotalJobs = count(),
    Successful = countif(Result == 1),
    Failed = countif(Result == 0),
    SuccessRate = round(100.0 * countif(Result == 1) / count(), 1),
    AvgDurationMin = round(avg(DurationMin), 1),
    MedianDurationMin = round(percentile(DurationMin, 50), 1),
    P95DurationMin = round(percentile(DurationMin, 95), 1),
    MaxDurationMin = round(max(DurationMin), 1)
    by ActivityType
| order by TotalJobs desc

================================================================================
QUERY 2: Breakdown by Region (using DeploymentName)
================================================================================

let InternalSubs = cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions();
let RunnerSubs = cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions();
let InternalBackupSubs = cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions();
union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
| where Artifact_BackupProvider contains "adls"
| where StartTime between (datetime(2026-04-05) .. datetime(2026-04-06))
| where ActivityName == "Backup"
| where Artifact_SubscriptionId !in (InternalSubs) 
    and Artifact_SubscriptionId !in (RunnerSubs) 
    and Artifact_SubscriptionId !in (InternalBackupSubs)
| extend DurationMin = round(datetime_diff('millisecond', EndTime, StartTime) / 60000.0, 1)
| summarize 
    TotalJobs = count(),
    Successful = countif(Result == 1),
    Failed = countif(Result == 0),
    SuccessRate = round(100.0 * countif(Result == 1) / count(), 1),
    MedianDurationMin = round(percentile(DurationMin, 50), 1),
    P95DurationMin = round(percentile(DurationMin, 95), 1),
    MaxDurationMin = round(max(DurationMin), 1)
    by DeploymentName
| order by TotalJobs desc


================================================================================
QUERY 3: Failure Error Breakdown
================================================================================

let InternalSubs = cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions();
let RunnerSubs = cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions();
let InternalBackupSubs = cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions();
union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
| where Artifact_BackupProvider contains "adls"
| where StartTime >= ago(1d)
| where ActivityName == "Backup" and Result == 0
| where Artifact_SubscriptionId !in (InternalSubs) 
    and Artifact_SubscriptionId !in (RunnerSubs) 
    and Artifact_SubscriptionId !in (InternalBackupSubs)
| extend ErrorCode = tostring(ErrorDetails.ErrorCode),
    ErrorMsg = tostring(ErrorDetails.Message)
| summarize Count = count(), SampleMessage = take_any(ErrorMsg) by ErrorCode
| order by Count desc

================================================================================
QUERY 4: First Backup vs Incremental
================================================================================
// Uses 30-day lookback for ANY prior backup attempt (success or failure).
// If an instance had any prior attempt, it's incremental — even if all
// previous backups failed. Only truly new protections count as "First Backup".

let InternalSubs = cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions();
let RunnerSubs = cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions();
let InternalBackupSubs = cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions();
let YesterdayBackups = union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where Artifact_BackupProvider contains "adls"
    | where StartTime between (datetime(2026-04-05) .. datetime(2026-04-06))
    | where ActivityName == "Backup"
    | where Artifact_SubscriptionId !in (InternalSubs) 
        and Artifact_SubscriptionId !in (RunnerSubs) 
        and Artifact_SubscriptionId !in (InternalBackupSubs)
    | distinct Artifact_BackupInstanceId;
let FirstAttemptDates = union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where Artifact_BackupProvider contains "adls"
    | where StartTime between (datetime(2026-03-06) .. datetime(2026-04-05))  // 30-day lookback
    | where ActivityName == "Backup"
    | where Artifact_BackupInstanceId in (YesterdayBackups)
    | summarize EarliestPriorAttempt = min(StartTime) by Artifact_BackupInstanceId;
YesterdayBackups
| join kind=leftouter FirstAttemptDates on Artifact_BackupInstanceId
| summarize 
    FirstBackup = countif(isnull(EarliestPriorAttempt)),
    Incremental = countif(isnotnull(EarliestPriorAttempt))

================================================================================
QUERY 5: Data Size & Object Count (via XStore)
================================================================================
// NOTE: ActivityStats SizeData is always 0 for ADLS. Must use XStore.
// NOTE: XStore Account column has version suffix (e.g., "name;2025-11-07T...").
//       Use AccountNameWithoutVersion for matching.

let InternalSubs = cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions();
let RunnerSubs = cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions();
let InternalBackupSubs = cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions();
let BackupAccountNames = union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats,
    cluster('mabprodweu').database('MABKustoProd').ActivityStats,
    cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where Artifact_BackupProvider contains "adls"
    | where StartTime between (datetime(2026-04-05) .. datetime(2026-04-06))
    | where ActivityName == "Backup"
    | where Artifact_SubscriptionId !in (InternalSubs) 
        and Artifact_SubscriptionId !in (RunnerSubs) 
        and Artifact_SubscriptionId !in (InternalBackupSubs)
    | extend AccountName = tolower(tostring(Input.SourceDatasourceName))
    | distinct AccountName;
let XStoreData = cluster('Xstore').database('xdataanalytics').XStoreAccountCapacityDaily
    | where TimePeriod between (datetime(2026-04-04) .. datetime(2026-04-06))
    | where IsPrimaryReplica == 1 and Category == "UserData"
    | extend AccName = tolower(AccountNameWithoutVersion)
    | where AccName in (BackupAccountNames)
    | summarize 
        SizeGB = round(sumif(UsedSize / pow(1024, 3), DataType =~ "BlockBlob"), 2),
        ContainerCount = sumif(ObjectCount, DataType =~ "Blobcontainerprivate"),
        BlobCount = sumif(ObjectCount, DataType =~ "BlockBlob")
        by AccName;
XStoreData
| summarize 
    AccountsWithData = count(),
    TotalSizeTB = round(sum(SizeGB) / 1024.0, 2),
    TotalContainers = sum(ContainerCount),
    TotalBlobs = sum(BlobCount),
    AvgSizeGB = round(avg(SizeGB), 1),
    MedianSizeGB = round(percentile(SizeGB, 50), 1),
    P95SizeGB = round(percentile(SizeGB, 95), 1),
    MaxSizeGB = round(max(SizeGB), 1),
    AvgContainers = round(avg(ContainerCount), 0),
    MaxContainers = max(ContainerCount),
    AvgBlobs = round(avg(BlobCount), 0),
    MaxBlobs = max(BlobCount) 
    
// PI details
let BlobBackupStats = () {
    
// max backup time per BI
    let timeduration = 100d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/adlsBlobServices")
    //( "Microsoft.Storage/storageAccounts/blobServices", "Microsoft.Storage/storageAccounts/adlsBlobServices")
    //| distinct ServiceName, ActivityName, ActivityType, ActivitySubType | sort by ServiceName, ActivityName, ActivityType
    //| take 10
    | where ActivityType in ("ScheduledBackup", "AdhocBackup") 
    | where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
        | project Artifact_BackupInstanceId, ActivityType, ActivityName, StartTime, EndTime, backuptime = totimespan(EndTime - StartTime), DeploymentName, TIMESTAMP, AccountName = tolower(tostring(Input.SourceDatasourceName))
    | summarize arg_max(backuptime,*) by Artifact_BackupInstanceId
    | summarize count() by bin(backuptime,1d)

//backup time date-wise
    let timeduration = 30d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where Artifact_SubscriptionId !in (InternalSubs) | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/adlsBlobServices")
    | where ActivityType in ("ScheduledBackup", "AdhocBackup") 
    | project Artifact_BackupInstanceId, ActivityType, ActivityName, StartTime, EndTime, backuptime = totimespan(EndTime - StartTime), DeploymentName, TIMESTAMP, AccountName = tolower(tostring(Input.SourceDatasourceName))
    | summarize 
    make_list(pack("Time",TIMESTAMP, "backuptime",backuptime))
    by Artifact_BackupInstanceId
    
//BI count protected/stopped/adhoc-backup
    let timeduration = 200d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/adlsBlobServices")
    | where Artifact_SubscriptionId !in (InternalSubs) | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where DeploymentName !contains "-can0"
    //| where ActivityType in ("ScheduledBackup", "AdhocBackup") 
    //| where ActivityType contains "configure" or ActivityType contains "stop"
    | where ActivityName !contains "tag"
    | summarize
    FirstSeen = min(TIMESTAMP),
    LastSeen = max(TIMESTAMP)
    by Artifact_BackupInstanceId, ActivityType, ActivityName
    | sort by Artifact_BackupInstanceId, FirstSeen asc 
    //| summarize dcount(Artifact_BackupInstanceId)
    //| distinct ActivityName, ActivityType
    | summarize 
    BI_protected=dcount(Artifact_BackupInstanceId),
    BI_Stopped=dcountif(Artifact_BackupInstanceId, ActivityName contains "StopProtection"),
    BI_Adhoc_Backup=dcountif(Artifact_BackupInstanceId, ActivityType contains "AdhocBackup"),
    BI_CreateorUpdateBackupPolicy=dcountif(Artifact_BackupInstanceId, ActivityName contains "CreateOrUpdateBackupPolicy"),
    BI_Restore=dcountif(Artifact_BackupInstanceId, ActivityName contains "TriggerRestore"),
    BI_PurgeProtection=dcountif(Artifact_BackupInstanceId, ActivityName contains "PurgeProtection")
    

//find the behaviour for vaibhav blob/adls account protection
    union cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where Artifact_SubscriptionId == "ef4ab5a7-c2c0-4304-af80-af49f48af3d1" //| count //BAckup PM Sub
    //| where Artifact_SubscriptionId == "028870ba-96e8-4b6e-9e27-7afceaea1bf7" //Rabobank Sub
    | extend ErrorStatus = tolower(tostring(ErrorDetails.ErrorCode))
    | where Artifact_BackupProvider contains "blob" //"adls"
    | extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))
    | where StorageAccount contains "vaibhav"// "edlcorestdeudev0001"
    | project TIMESTAMP, DeploymentName, ServiceName, ActivityName, ActivityType, StartTime, EndTime, backuptime = EndTime-StartTime, ErrorStatus, StorageAccount//, Input, Output, SizeData, PerfData,
    | sort by StorageAccount, TIMESTAMP asc 
    
    | summarize 
    
    by StorageAccount
    
    
    
    ///find the behaviour for long running backup accounts
    let timeduration=ago(100d);
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    let adls_backup_external_data=(
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,   cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where TIMESTAMP >= timeduration
    | where DeploymentName !in ("sea-bvtd", "sea-bvtd2", "ea-bvtd3", "sea-can01", "ccy-pod01", "ecy-pod01", "ea-can02")
    | where DeploymentName !contains "-can0"
    | where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    //| where Artifact_BackupProvider contains "blob"                           // Filtering blob accounts
    | where Artifact_BackupProvider contains "adls"                             // Filtering adls accounts
    | where ActivityName !contains "tag"
    | extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))     //Input Storage account 
    );
    adls_backup_external_data
    | where StorageAccount in (adls_backup_external_data | where  EndTime-StartTime > 20d | distinct  StorageAccount)
    | extend ErrorStatus = tolower(tostring(ErrorDetails.ErrorCode))
    //| summarize dcount(Artifact_BackupInstanceId), dcount(StorageAccount) by ErrorStatus
    | project TIMESTAMP, Artifact_BackupInstanceId, DeploymentName, ServiceName, ActivityName, ActivityType, StartTime, EndTime, backuptime = EndTime-StartTime, ErrorStatus, StorageAccount//, Input, Output, SizeData, PerfData,
    | sort by StorageAccount, TIMESTAMP asc
  
    
    // Count of success/failure for long running backup accounts
    let timeduration=ago(100d);
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    let adls_backup_external_data=(
    union  	cluster('mabprod1').database('MABKustoProd1').ActivityStats,  	cluster('mabprodweu').database('MABKustoProd').ActivityStats,   cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where TIMESTAMP >= timeduration
    | where DeploymentName !in ("sea-bvtd", "sea-bvtd2", "ea-bvtd3", "sea-can01", "ccy-pod01", "ecy-pod01", "ea-can02")
    | where DeploymentName !contains "-can0"
    | where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    //| where Artifact_BackupProvider contains "blob"                           // Filtering blob accounts
    | where Artifact_BackupProvider contains "adls"                             // Filtering adls accounts
    | where ActivityName !contains "tag"
    | extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))     //Input Storage account 
    );
    adls_backup_external_data
    | where StorageAccount in (adls_backup_external_data | where  EndTime-StartTime > 20d | distinct  StorageAccount)
    | extend ErrorStatus = tolower(tostring(ErrorDetails.ErrorCode))
    //| summarize dcount(Artifact_BackupInstanceId), dcount(StorageAccount) by ErrorStatus
    | project TIMESTAMP, Artifact_BackupInstanceId, DeploymentName, ServiceName, ActivityName, ActivityType, StartTime, EndTime, backuptime = EndTime-StartTime, ErrorStatus, StorageAccount//, Input, Output, SizeData, PerfData,
    | sort by StorageAccount, TIMESTAMP asc
    //| summarize dcount(StorageAccount), dcount(Artifact_BackupInstanceId)
    | summarize count() by Artifact_BackupInstanceId, ActivityName, ErrorStatus
    | sort by Artifact_BackupInstanceId, ActivityName, ErrorStatus
    
    
    union 
    cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    //| where TIMESTAMP >= ago(20d)
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/adlsBlobServices" )
    | where Artifact_SubscriptionId !in (cluster('mabprod1').database('AzureBackup').GetInternalSubscriptions())
    | where Artifact_SubscriptionId !in (cluster('mabprod1').database('AzureBackup').GetRunnerSubscriptions())
    | where Artifact_SubscriptionId !in (cluster('mabprod1').database('AzureBackup').GetInternalBackupSubscriptions())
    | where DeploymentName !in ("sea-bvtd", "sea-bvtd2", "ea-bvtd3", "sea-can01", "ccy-pod01", "ecy-pod01", "ea-can02")
    | where DeploymentName !contains "-can0"
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | join kind=inner (DimSubscriptionEx | project Artifact_SubscriptionId=SubscriptionId, OfferType, MSCustomerId) on Artifact_SubscriptionId
    | where Artifact_SubscriptionId !contains "internal"
    | join kind=inner (DimCustomerEx | project MSCustomerId, CustomerName) on MSCustomerId
    
    | project TIMESTAMP, tostring(Input.SourceDatasourceName), ServiceName, ActivityName, ActivityType, StartTime, EndTime, backuptime = EndTime-StartTime, ErrorDetails.ErrorCode, CustomerName
    | count 
    
    | distinct ActivityName, ActivityType
    
    | summarize 
    backupcount=countif(ActivityName contains "backup")
    by Artifact_BackupInstanceId//by MSCustomerId, CustomerName
    
    
    
    | summarize
    FirstSeen = min(TIMESTAMP),
    LastSeen = max(TIMESTAMP)
    by Artifact_BackupInstanceId, ActivityType, ActivityName
    | sort by Artifact_BackupInstanceId, FirstSeen asc 
    //| summarize dcount(Artifact_BackupInstanceId)
    //| distinct ActivityName, ActivityType
    | summarize 
    BI_protected=dcount(Artifact_BackupInstanceId),
    BI_Stopped=dcountif(Artifact_BackupInstanceId, ActivityName contains "StopProtection"),
    BI_Adhoc_Backup=dcountif(Artifact_BackupInstanceId, ActivityType contains "AdhocBackup"),
    BI_CreateorUpdateBackupPolicy=dcountif(Artifact_BackupInstanceId, ActivityName contains "CreateOrUpdateBackupPolicy"),
    BI_Restore=dcountif(Artifact_BackupInstanceId, ActivityName contains "TriggerRestore"),
    BI_PurgeProtection=dcountif(Artifact_BackupInstanceId, ActivityName contains "PurgeProtection")
    
    
    
    
    
    
    
    | where Artifact_SubscriptionId == "028870ba-96e8-4b6e-9e27-7afceaea1bf7"
    | extend ErrorStatus = tolower(tostring(ErrorDetails.ErrorCode))
    | where Artifact_BackupProvider contains "adls" //"blob"
    //| extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))
    | where Input contains "edlcorestdeudev0001"// "vaibhav"
    | project TIMESTAMP, DeploymentName, ServiceName, ActivityName, ActivityType, StartTime, EndTime, backuptime = EndTime-StartTime, ErrorStatus// Input, Output, SizeData, PerfData,
    
    
// Full query per BI on when was it configured, count of successfull backups, failure count/details    
let timeduration = ago(100d);
let InternalSubs = GetInternalSubscriptions();
let RunnerSubs = GetRunnerSubscriptions();
let InteranlBackupSubs = GetInternalBackupSubscriptions();
let adls_backup_external_data =
(
    union
        cluster('mabprod1').database('MABKustoProd1').ActivityStats,
        cluster('mabprodweu').database('MABKustoProd').ActivityStats,
        cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where TIMESTAMP >= timeduration
    | where DeploymentName !in ("sea-bvtd", "sea-bvtd2", "ea-bvtd3", "sea-can01", "ccy-pod01", "ecy-pod01", "ea-can02")
    | where DeploymentName !contains "-can0"
    | where Artifact_SubscriptionId !in (InternalSubs)
    | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId !in (InteranlBackupSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where Artifact_BackupProvider contains "adls"
    | where ActivityName !contains "tag" 
    | where ActivityName !contains "Monitoring" 
    | where ActivityName !contains "Restore"
    | extend StorageAccount = tolower(tostring(Input.SourceDatasourceName))
    | extend ErrorStatus = tolower(tostring(ErrorDetails.ErrorCode))    
);
// (Optional) Keep your "long-running" filter; comment out if you want full population
let scoped =
(
    adls_backup_external_data
    // Backup instance "name": replace these with the real field(s) you have, if any:
    | extend BackupInstanceName = tostring(Artifact_BackupInstanceId)   
    | extend ActivityType_s = tostring(ActivityType)
    | extend ActivityName_s = tostring(ActivityName)
    | extend ActivityType_l = tolower(ActivityType_s)
    | extend ActivityName_l = tolower(ActivityName_s)
    // Configure protection predicate (keep broad unless you know exact values)
    | extend IsConfigure = ActivityName contains "configure" or ActivityType contains "configure"
    // StopProtection predicate: EXACT match on BOTH fields as requested
    | extend IsStopProtection = (ActivityType_s == "StopProtection" or ActivityName_s == "StopProtection")
    // Backup predicate
    | extend IsBackup = ActivityType_l has "backup" or ActivityName_l == "backup"
    | extend IsSuccess = ErrorStatus == "success"
    | extend BackupDuration = EndTime - StartTime
);
// Failure breakdown per (SA, BI): list of {ErrorCode, Count}
let failure_breakdown =
(
    scoped
    | where IsBackup and not(IsSuccess)
    | summarize Cnt = count() by StorageAccount, BackupInstanceName, ErrorStatus
    | summarize FailureBreakdown = make_list(pack("ErrorCode", ErrorStatus, "Count", Cnt), 50)
        by BackupInstanceName
);
// Lifecycle "last event" helper (so you can compute IsCurrentlyStopped)
let last_lifecycle_event =
(
    scoped
    | where IsConfigure or IsStopProtection
    | summarize arg_max(TIMESTAMP, ActivityName_s, ActivityType_s) by BackupInstanceName
    | project BackupInstanceName, LastLifecycleEventTime=TIMESTAMP, LastLifecycleActivityName=ActivityName_s, LastLifecycleActivityType=ActivityType_s
);
// Main rollup per (SA, BI)
let rollup =
(
    scoped
    | summarize
        // Configure Protection
        FirstConfiguredOn = minif(TIMESTAMP, IsConfigure),
        LastConfiguredOn  = maxif(TIMESTAMP, IsConfigure),
        ConfigureEvents   = countif(IsConfigure),
        // ✅ StopProtection
        FirstStoppedOn = minif(TIMESTAMP, IsStopProtection),
        LastStoppedOn  = maxif(TIMESTAMP, IsStopProtection),
        StopEvents     = countif(IsStopProtection),
        // Backup success/failure counts
        SuccessfulBackups = countif(IsBackup and IsSuccess),
        FailedBackups     = countif(IsBackup and not(IsSuccess)),
        TotalBackups      = countif(IsBackup),
        // Useful time/duration signals
        LastBackupOn      = maxif(TIMESTAMP, IsBackup),
        MaxBackupDuration = maxif(BackupDuration, IsBackup)
      by BackupInstanceName
);
// Final output
rollup
| join kind=leftouter failure_breakdown on BackupInstanceName
| join kind=leftouter last_lifecycle_event on  BackupInstanceName
| extend IsCurrentlyStopped = (LastLifecycleActivityName == "StopProtection" and LastLifecycleActivityType == "StopProtection")
| project
    BackupInstanceName,
    FirstConfiguredOn,
    LastConfiguredOn,
    ConfigureEvents,
    FirstStoppedOn,
    LastStoppedOn,
    StopEvents,
    IsCurrentlyStopped,
    SuccessfulBackups,
    FailedBackups,
    TotalBackups,
    LastBackupOn,
    MaxBackupDuration,
    FailureBreakdown
| order by BackupInstanceName asc

// ADLS PI count
    let timeduration = 100d;
    let InternalSubs = GetInternalSubscriptions();
    let RunnerSubs = GetRunnerSubscriptions();
    let InteranlBackupSubs =  GetInternalBackupSubscriptions();
    union cluster('mabprod1').database('MABKustoProd1').ActivityStats, cluster('mabprodweu').database('MABKustoProd').ActivityStats, cluster('mabprodwus').database('MABKustoProd').ActivityStats
    | where PreciseTimeStamp >= ago(timeduration)
    | where Artifact_BackupProvider in ( "Microsoft.Storage/storageAccounts/adlsBlobServices")
    | where Artifact_SubscriptionId !in (InternalSubs) | where Artifact_SubscriptionId !in (RunnerSubs)
    | where Artifact_SubscriptionId != "00000000-0000-0000-0000-000000000000"
    | where DeploymentName !contains "-can0"
    | where ActivityType in ("ScheduledBackup", "AdhocBackup") 
    //| where ActivityType contains "configure" or ActivityType contains "stop"
    | summarize dcount(Artifact_BackupInstanceId) by startofweek(TIMESTAMP)
    | render columnchart 
    
    | where ActivityName !contains "tag"
    | summarize
    FirstSeen = min(TIMESTAMP),
    LastSeen = max(TIMESTAMP)
    by Artifact_BackupInstanceId, ActivityType, ActivityName
    | sort by Artifact_BackupInstanceId, FirstSeen asc 
    //| summarize dcount(Artifact_BackupInstanceId)
    //| distinct ActivityName, ActivityType
    | summarize 
    BI_protected=dcount(Artifact_BackupInstanceId),
    BI_Stopped=dcountif(Artifact_BackupInstanceId, ActivityName contains "StopProtection"),
    BI_Adhoc_Backup=dcountif(Artifact_BackupInstanceId, ActivityType contains "AdhocBackup"),
    BI_CreateorUpdateBackupPolicy=dcountif(Artifact_BackupInstanceId, ActivityName contains "CreateOrUpdateBackupPolicy"),
    BI_Restore=dcountif(Artifact_BackupInstanceId, ActivityName contains "TriggerRestore"),
    BI_PurgeProtection=dcountif(Artifact_BackupInstanceId, ActivityName contains "PurgeProtection")

 
