# Electricity Maps - Kibana Dashboard Import

## Quick Start

### 1. Import Dashboards

**Method A: Kibana UI**
```bash
Stack Management → Saved Objects → Import
Select file: electricity-maps-dashboards-esql.ndjson
Check "Automatically overwrite conflicts"
Click Import
```

**Method B: API**
```bash
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: multipart/form-data" \
  -F file=@electricity-maps-dashboards-esql.ndjson
```

### 2. View Dashboards

Navigate to:
- **Analytics → Dashboard**
- Filter: "electricity" or "European Grid"

Available dashboards:
1. `Dashboard 1: European Grid Overview`
2. `Dashboard 3: Renewable Leaderboard`

---

## Dashboard Descriptions

### Dashboard 1: European Grid Overview

**Purpose:** Real-time snapshot of European electricity grid state

**Metrics Row (Top):**
- Average Renewable % across Europe (color-coded: red <30%, yellow 30-70%, green >70%)
- Total Production (GW)
- Total Consumption (GW)  
- Net Grid Balance (GW) - positive = net export

**Visualizations:**
- **Horizontal Bar:** Top 15 countries by renewable percentage
- **Donut Chart:** Aggregate European energy mix breakdown (Wind, Solar, Hydro, Nuclear, Gas, Coal, Biomass)
- **Data Table:** Complete country rankings with sortable columns
  - Country Code
  - Renewable % (cell-colored)
  - Fossil-Free % (cell-colored)
  - Production (MW)
  - Consumption (MW)
  - Net Position (MW, cell-colored: red=import, green=export)

**Use Cases:**
- Executive summary of grid state
- Identify renewable leaders and laggards
- Track cross-border power flows
- Monitor aggregate energy mix

---

### Dashboard 3: Renewable Leaderboard

**Purpose:** Competitive rankings and detailed comparison

**Visualizations:**
- **Left Bar Chart:** Top 15 countries by Renewable % (excludes nuclear)
- **Right Bar Chart:** Top 15 countries by Fossil-Free % (includes nuclear)
- **Bottom Table:** Complete rankings with all metrics

**Key Insights:**
- Countries with high nuclear (FR, CH) rank higher in fossil-free than renewable
- Nordics (NO, DK, FI) dominate both categories due to hydro + wind
- Highlights policy differences: renewable-only vs low-carbon strategies

---

## Data Refresh Strategy

### Current State: Single Snapshot
Your index contains **one timestamp** (2026-01-15 09:00 UTC)

### Production Recommendations

**Ingestion Frequency:**
- **Hourly snapshots** (minimum)
- **15-minute intervals** (recommended for intraday analysis)
- **5-minute intervals** (optimal for real-time monitoring)

**Data Pipeline:**
```bash
# Example: Hourly cron job
0 * * * * /usr/bin/fetch-electricity-data.sh >> /var/log/electricity-ingest.log 2>&1
```

**Index Lifecycle Policy:**
```json
{
  "policy": "electricity-maps-ilm",
  "phases": {
    "hot": {
      "min_age": "0ms",
      "actions": {
        "rollover": {
          "max_size": "50GB",
          "max_age": "30d"
        }
      }
    },
    "warm": {
      "min_age": "30d",
      "actions": {
        "shrink": {
          "number_of_shards": 1
        }
      }
    },
    "delete": {
      "min_age": "365d",
      "actions": {
        "delete": {}
      }
    }
  }
}
```

**Storage Estimates:**
- Per document: ~2 KB
- 15-minute intervals: 96 docs/day × 15 countries = 1,440 docs/day (~3 MB/day)
- Annual retention: ~1 GB/year

---

## Time-Series Features (Requires Historical Data)

Once you ingest historical data, add these visualizations:

### Time Series Line Charts
```esql
FROM electricity-maps*
| STATS 
    avg_renewable = AVG(renewable_percentage),
    avg_fossil_free = AVG(fossil_free_percentage)
  BY country_code, bucket = DATE_TRUNC(1 hour, @timestamp)
| WHERE country_code IN ["DE", "FR", "NO", "ES", "GB"]
| SORT bucket ASC
```

### Peak/Off-Peak Analysis
```esql
FROM electricity-maps*
| EVAL hour = DATE_EXTRACT("hour", @timestamp)
| EVAL period = CASE(
    hour >= 7 AND hour <= 22, "peak",
    "off-peak"
  )
| STATS 
    avg_renewable = AVG(renewable_percentage),
    avg_production = AVG(power_production_total)
  BY period, country_code
```

### Week-over-Week Trends
```esql
FROM electricity-maps*
| EVAL week = DATE_TRUNC(1 week, @timestamp)
| STATS 
    renewable = AVG(renewable_percentage),
    production = SUM(power_production_total)
  BY week, country_code
| SORT week DESC, renewable DESC
```

---

## Advanced Visualizations to Add

### 1. Geographic Heatmap (Maps App)

**Steps:**
1. Add layer: Documents
2. Index pattern: `electricity-maps*`
3. Geospatial field: `location`
4. Tooltip fields: `country_code`, `renewable_percentage`, `power_production_total`
5. Style by: `renewable_percentage`
6. Color ramp: Red (0%) → Yellow (50%) → Green (100%)
7. Circle size by: `power_production_total`

### 2. Cross-Border Flow Analysis (Requires Import/Export Data)

If your data includes per-connection flows:
```esql
FROM electricity-maps*
| WHERE generation_mix.imports IS NOT NULL
| STATS total_imports = SUM(generation_mix.imports) BY country_code
| SORT total_imports DESC
```

### 3. Carbon Intensity Tracking

**Note:** `carbon_intensity` field currently unpopulated. If populated:
```esql
FROM electricity-maps*
| STATS 
    avg_carbon = AVG(carbon_intensity),
    min_carbon = MIN(carbon_intensity),
    max_carbon = MAX(carbon_intensity)
  BY country_code
| EVAL carbon_range = max_carbon - min_carbon
| SORT avg_carbon ASC
```

Visualization: Heatmap showing carbon intensity by country and hour-of-day.

---

## Alerting Rules (Elastic Alerting)

### Alert 1: Low Renewable Percentage
```
Threshold: renewable_percentage < 30%
Frequency: Every 1 hour
Actions: Send Slack notification
```

### Alert 2: Grid Imbalance
```
Threshold: |power_production_total - power_consumption_total| > 10000 MW
Frequency: Every 15 minutes
Actions: Email ops team
```

### Alert 3: Fossil Fuel Spike
```
Threshold: fossil_percentage > 70%
Frequency: Every 1 hour
Actions: Log to monitoring system
```

---

## Troubleshooting

### Issue: Dashboards show "No data"

**Check 1: Index exists**
```bash
GET electricity-maps/_count
```

**Check 2: Time range**
Your data is timestamped 2026-01-15 09:00 UTC. Ensure dashboard time filter includes this.

Set absolute time range:
- From: 2026-01-15 00:00:00
- To: 2026-01-16 00:00:00

**Check 3: Index pattern**
```bash
GET _data_stream/electricity-maps*
GET _index_template/electricity-maps*
```

### Issue: Visualizations error on ES|QL queries

**ES|QL requires Elasticsearch 8.11+**

Check version:
```bash
GET /
```

Fallback: Use standard Lens aggregations instead of textBased datasource.

### Issue: Colors not showing in table

Lens cell coloring requires:
1. Numeric field type
2. Valid palette configuration
3. Non-null values

Check field mapping:
```bash
GET electricity-maps/_mapping/field/renewable_percentage
```

---

## Performance Optimization

### For Large Datasets (>100M docs)

**1. Enable Index Sorting**
```json
PUT electricity-maps
{
  "settings": {
    "index": {
      "sort.field": ["@timestamp", "country_code.keyword"],
      "sort.order": ["desc", "asc"]
    }
  }
}
```

**2. Use Runtime Fields for Calculations**
```json
PUT electricity-maps/_mapping
{
  "runtime": {
    "net_position_gw": {
      "type": "double",
      "script": {
        "source": "(doc['power_production_total'].value - doc['power_consumption_total'].value) / 1000.0"
      }
    }
  }
}
```

**3. Aggregate on Ingest (Transform)**
```json
PUT _transform/electricity-hourly-avg
{
  "source": {
    "index": "electricity-maps*"
  },
  "dest": {
    "index": "electricity-maps-hourly"
  },
  "pivot": {
    "group_by": {
      "country": {"terms": {"field": "country_code.keyword"}},
      "hour": {"date_histogram": {"field": "@timestamp", "fixed_interval": "1h"}}
    },
    "aggregations": {
      "avg_renewable": {"avg": {"field": "renewable_percentage"}},
      "sum_production": {"sum": {"field": "power_production_total"}},
      "sum_consumption": {"sum": {"field": "power_consumption_total"}}
    }
  },
  "frequency": "1h",
  "sync": {
    "time": {"field": "@timestamp", "delay": "60s"}
  }
}
```

---

## Next Steps

1. **Ingest historical data** (at least 7 days for trend analysis)
2. **Add time-series visualizations** to Dashboard 1
3. **Create Dashboard 2: Country Deep Dive** with:
   - Country selector control
   - Hourly production/consumption trends
   - Energy source breakdown over time
4. **Set up alerting** for grid anomalies
5. **Configure ILM policy** for retention management
6. **Create Elasticsearch index template** for consistent mapping

---

## Support Resources

- ES|QL Documentation: https://www.elastic.co/guide/en/elasticsearch/reference/current/esql.html
- Lens Visualization: https://www.elastic.co/guide/en/kibana/current/lens.html
- Maps Integration: https://www.elastic.co/guide/en/kibana/current/maps.html
- Alerting Rules: https://www.elastic.co/guide/en/kibana/current/alerting-getting-started.html
