# General KQL Patterns - Natural Language to Kusto

Common patterns that work across any Kusto cluster. Use these as a starting
point when onboarding to a new telemetry dataset.

---

## Discovery Phase

### "What tables are available?"
Use the `list_tables` tool - no KQL needed.

### "What columns does TableX have?"
Use the `get_table_schema` tool.

### "Show me a sample of the data"
```kql
TableName | take 10
```

### "What are the distinct values in ColumnX?"
```kql
TableName | distinct ColumnX | order by ColumnX asc | take 100
```

### "How much data is in this table?"
```kql
TableName | where Timestamp > ago(1d) | count
```

---

## Analysis Patterns

### Count & Group
**"How many events per category?"**
```kql
Events | summarize Count=count() by Category | order by Count desc
```

### Time Trends
**"Show me daily trends over the last month"**
```kql
Events
| where Timestamp > ago(30d)
| summarize DailyCount = count() by bin(Timestamp, 1d)
| order by Timestamp asc
```

### Percentiles
**"What's the P50 and P99 latency?"**
```kql
Requests
| where Timestamp > ago(1d)
| summarize P50=percentile(Duration, 50), P99=percentile(Duration, 99)
```

### Failure Rate
**"What percentage of requests are failing?"**
```kql
Requests
| where Timestamp > ago(1d)
| summarize Total=count(), Failed=countif(Status >= 500)
| extend FailureRate = round(100.0 * Failed / Total, 2)
```

### Top N by Metric
**"Which users have the most errors?"**
```kql
Errors
| where Timestamp > ago(7d)
| summarize ErrorCount=count() by UserId
| top 10 by ErrorCount desc
```

### Join Tables
**"Correlate errors with user info"**
```kql
Errors
| where Timestamp > ago(1d)
| join kind=inner (Users | project UserId, UserName, Region) on UserId
| summarize count() by UserName, Region
```

### Moving Average
**"Show 7-day moving average of daily signups"**
```kql
Signups
| summarize DailyCount=count() by bin(Timestamp, 1d)
| order by Timestamp asc
| extend MovingAvg = avg_over(DailyCount, 7)
```

---

## Tips for PMs

1. **Start broad, then narrow** - Begin with `| take 10` to see the data shape
2. **Always filter by time** - `where Timestamp > ago(7d)` prevents scanning TB of data
3. **Use `dcount()` for uniques** - Much faster than `count(distinct ...)`
4. **Ask the assistant to explain** - After getting results, ask "what does this tell us?"
5. **Save useful queries** - Ask the assistant to save queries you use frequently
