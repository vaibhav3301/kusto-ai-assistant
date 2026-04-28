# Azure Storage - Data Context

You are helping a PM analyze Azure Storage telemetry data.

## Clusters

| Name | URL | Database |
|------|-----|----------|
| xstore | https://xstore.kusto.windows.net/ | xstore |
| xstorepm | https://xstorepm.westcentralus.kusto.windows.net/ | XStorePM |
| xdataanalytics | https://xdataanalytics.westcentralus.kusto.windows.net/ | XDataAnalytics |

## Key Tables

### xstorepm / XStorePM
| Table | What it has |
|-------|------------|
| StorageAccountCapTX_Updated | Storage account capacity and transaction data |
| StorageAccountBlobAgeCohort | Blob age distribution across accounts |
| StorageAccountBlobSizeCohort | Blob size distribution |

### xstore / xstore
| Table | What it has |
|-------|------------|
| StorageLogsSecurityV2 | Security audit logs (anonymous access, auth failures) |
| TenantCapacityBillableHourlyV2 | Hourly billable capacity per tenant |

### xstorepm / XResiliency
| Table | What it has |
|-------|------------|
| CriticalCustomerSubscriptionsLog | Critical customer tracking |
| CriticalCustomerAccountsLog | Critical account tracking |

### xdataanalytics / XDataAnalytics
| Table | What it has |
|-------|------------|
| XStoreAccountBillingHourly | Hourly billing data per account |
| SummarizedXStoreAccountTransactionsHourlyV2 | Transaction summaries |

## Tips

- These tables have direct columns (no JSON parsing needed, unlike Backup tables)
- Always filter by time: `where Timestamp > ago(7d)` or `where PreciseTimeStamp > ago(1d)`
- For capacity data, convert bytes to TB: `round(CapacityInBytes / 1099511627776.0, 2)`
- For critical customers, use the XResiliency database on the xstorepm cluster
