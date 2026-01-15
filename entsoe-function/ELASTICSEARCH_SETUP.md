# ENTSO-E Elasticsearch Index Setup

This script creates the proper index mapping for ENTSO-E energy data in Elasticsearch.

## Create Index with Mapping

Run this in Kibana Dev Tools or via curl:

```json
PUT entsoe-energy
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index": {
      "refresh_interval": "5s"
    }
  },
  "mappings": {
    "properties": {
      "@timestamp": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "datetime_from": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "datetime_to": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "country_code": {
        "type": "keyword"
      },
      "country_name": {
        "type": "keyword",
        "fields": {
          "text": {
            "type": "text"
          }
        }
      },
      "area_code": {
        "type": "keyword"
      },
      "location": {
        "type": "geo_point"
      },
      "generation_mix": {
        "type": "object",
        "properties": {
          "biomass": { "type": "float" },
          "fossil_brown_coal": { "type": "float" },
          "fossil_coal": { "type": "float" },
          "fossil_gas": { "type": "float" },
          "fossil_hard_coal": { "type": "float" },
          "fossil_oil": { "type": "float" },
          "geothermal": { "type": "float" },
          "hydro_pumped_storage": { "type": "float" },
          "hydro_run_of_river": { "type": "float" },
          "hydro_water_reservoir": { "type": "float" },
          "marine": { "type": "float" },
          "nuclear": { "type": "float" },
          "other_renewable": { "type": "float" },
          "solar": { "type": "float" },
          "waste": { "type": "float" },
          "wind_offshore": { "type": "float" },
          "wind_onshore": { "type": "float" },
          "other": { "type": "float" }
        }
      },
      "total_load_mw": {
        "type": "float"
      },
      "carbon_intensity": {
        "type": "float"
      },
      "renewable_percentage": {
        "type": "float"
      },
      "fossil_percentage": {
        "type": "float"
      },
      "low_carbon_percentage": {
        "type": "float"
      },
      "data_source": {
        "type": "keyword"
      },
      "updated_at": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      }
    }
  }
}
```

## Create Index Pattern in Kibana

1. Go to **Stack Management** > **Index Patterns**
2. Click **Create index pattern**
3. Enter `entsoe-energy*` as the pattern
4. Select `@timestamp` as the time field
5. Click **Create index pattern**

## Sample Queries

### Get Latest Data for All Countries
```json
GET entsoe-energy/_search
{
  "size": 0,
  "aggs": {
    "countries": {
      "terms": {
        "field": "country_name",
        "size": 30
      },
      "aggs": {
        "latest": {
          "top_hits": {
            "size": 1,
            "sort": [{ "@timestamp": { "order": "desc" }}]
          }
        }
      }
    }
  }
}
```

### Countries with Highest Renewable Percentage
```json
GET entsoe-energy/_search
{
  "size": 0,
  "aggs": {
    "top_renewable": {
      "terms": {
        "field": "country_name",
        "size": 10,
        "order": { "avg_renewable": "desc" }
      },
      "aggs": {
        "avg_renewable": {
          "avg": { "field": "renewable_percentage" }
        }
      }
    }
  }
}
```

### Carbon Intensity Over Time
```json
GET entsoe-energy/_search
{
  "size": 0,
  "aggs": {
    "over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "1h"
      },
      "aggs": {
        "avg_intensity": {
          "avg": { "field": "carbon_intensity" }
        },
        "by_country": {
          "terms": { "field": "country_name" },
          "aggs": {
            "avg_intensity": {
              "avg": { "field": "carbon_intensity" }
            }
          }
        }
      }
    }
  }
}
```

### Total Load by Country
```json
GET entsoe-energy/_search
{
  "size": 0,
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-1h"
      }
    }
  },
  "aggs": {
    "by_country": {
      "terms": {
        "field": "country_name",
        "size": 30,
        "order": { "avg_load": "desc" }
      },
      "aggs": {
        "avg_load": {
          "avg": { "field": "total_load_mw" }
        }
      }
    }
  }
}
```

## Dashboard Visualizations

### 1. Europe Energy Map
- **Type**: Region Map
- **Metrics**: Average `carbon_intensity`
- **Bucket**: Terms on `country_name.keyword`
- **Join field**: `location`

### 2. Renewable Energy Bar Chart
- **Type**: Horizontal Bar
- **Y-axis**: `country_name.keyword`
- **Metrics**: Average `renewable_percentage`
- **Sort**: Descending

### 3. Generation Mix Stacked Area
- **Type**: Area Chart (Stacked)
- **X-axis**: `@timestamp`
- **Y-axis**: Sum of each generation type
- **Split Series**: By generation mix fields

### 4. Carbon Intensity Gauge
- **Type**: Gauge
- **Metric**: Average `carbon_intensity`
- **Ranges**: 
  - 0-100: Green (Very Low)
  - 101-300: Yellow (Low)
  - 301-500: Orange (Medium)
  - 501+: Red (High)

### 5. Load vs Time
- **Type**: Line Chart
- **X-axis**: `@timestamp`
- **Y-axis**: Average `total_load_mw`
- **Split Series**: `country_name.keyword`

### 6. Fossil vs Renewable
- **Type**: Pie Chart
- **Slice**: Average values
  - `renewable_percentage`
  - `fossil_percentage`
  - `generation_mix.nuclear` (as low carbon)

## Data Refresh

The Azure Function runs every hour by default. To manually refresh:

```bash
curl -X POST https://<function-app-name>.azurewebsites.net/api/ingest?code=<function-key>
```

For specific countries:
```bash
curl -X POST https://<function-app-name>.azurewebsites.net/api/ingest?code=<function-key>&countries=DE,FR,ES
```
