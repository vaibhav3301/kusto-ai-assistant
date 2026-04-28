# Azure Storage - Sample Natural Language Queries

Examples for Storage PMs querying XStore telemetry clusters.

---

## Cluster Info
- **Clusters:** `xstore`, `xstorepm`, `xdataanalytics`
- **Key tables:**
  - `xstore`: StorageLogsSecurityV2, TenantCapacityBillableHourlyV2, StorageObjectEvents
  - `xstorepm`: StorageAccountCapTX_Updated, StorageAccountBlobAgeCohort
  - `xdataanalytics`: XStoreAccountBillingHourly, XStoreAccountCapacityAggregationUpdateHourly

---

## Example Conversations

### 1. Account capacity lookup

**You:** "What are the top 10 storage accounts by capacity?"

```kql
// On xstorepm cluster
StorageAccountCapTX_Updated
| summarize LatestCapacity = max(TotalCapacityInBytes) by AccountName
| top 10 by LatestCapacity desc
| extend CapacityTB = round(LatestCapacity / 1099511627776.0, 2)
```

---

### 2. Transaction volume trends

**You:** "Show daily transaction counts for the past 2 weeks"

```kql
// On xdataanalytics cluster
SummarizedXStoreAccountTransactionsHourlyV2
| where Timestamp > ago(14d)
| summarize TotalTransactions = sum(TotalRequests) by bin(Timestamp, 1d)
| order by Timestamp asc
```

---

### 3. Blob age distribution

**You:** "What does the blob age distribution look like across accounts?"

```kql
// On xstorepm cluster
StorageAccountBlobAgeCohort
| summarize
    Under30Days = sum(BlobCount_Under30Days),
    Days30_90 = sum(BlobCount_30to90Days),
    Days90_365 = sum(BlobCount_90to365Days),
    Over365Days = sum(BlobCount_Over365Days)
```

---

### 4. Security audit

**You:** "Show me anonymous access requests in the last 24 hours"

```kql
// On xstore cluster
StorageLogsSecurityV2
| where PreciseTimeStamp > ago(1d)
| where AuthenticationType == "anonymous"
| summarize RequestCount = count() by AccountName, OperationName
| order by RequestCount desc
| take 20
```

---

### 5. Critical customer lookup

**You:** "Which subscriptions are flagged as critical customers?"

```kql
// On xstorepm cluster, XResiliency database
CriticalCustomerSubscriptionsLog
| summarize arg_max(Timestamp, *) by SubscriptionId
| project SubscriptionId, CustomerName, Priority, ProductTag
| order by Priority asc
```
