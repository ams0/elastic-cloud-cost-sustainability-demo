# ENTSO-E Azure Function

This Azure Function retrieves electricity generation, load, and carbon intensity data from the ENTSO-E (European Network of Transmission System Operators for Electricity) Transparency Platform for European countries and ingests it into Elasticsearch.

## Overview

The function collects:
- **Generation Mix**: Actual generation by energy type (solar, wind, nuclear, fossil fuels, etc.)
- **Total Load**: Actual total electricity load in MW
- **Carbon Intensity**: Calculated carbon intensity based on generation mix (gCO2/kWh)
- **Renewable Percentage**: Percentage of electricity from renewable sources
- **Fossil Percentage**: Percentage of electricity from fossil fuels
- **Low Carbon Percentage**: Percentage from renewables + nuclear

## Supported Countries

The function supports 28 European countries:

| Country | Code | ENTSO-E Area Code |
|---------|------|-------------------|
| Austria | AT | 10YAT-APG------L |
| Belgium | BE | 10YBE----------2 |
| Bulgaria | BG | 10YCA-BULGARIA-R |
| Croatia | HR | 10YHR-HEP------M |
| Czech Republic | CZ | 10YCZ-CEPS-----N |
| Denmark | DK | 10Y1001A1001A65H |
| Estonia | EE | 10Y1001A1001A39I |
| Finland | FI | 10YFI-1--------U |
| France | FR | 10YFR-RTE------C |
| Germany | DE | 10Y1001A1001A83F |
| Greece | GR | 10YGR-HTSO-----Y |
| Hungary | HU | 10YHU-MAVIR----U |
| Ireland | IE | 10YIE-1001A00010 |
| Italy | IT | 10YIT-GRTN-----B |
| Latvia | LV | 10YLV-1001A00074 |
| Lithuania | LT | 10YLT-1001A0008Q |
| Luxembourg | LU | 10YLU-CEGEDEL-NQ |
| Netherlands | NL | 10YNL----------L |
| Norway | NO | 10YNO-0--------C |
| Poland | PL | 10YPL-AREA-----S |
| Portugal | PT | 10YPT-REN------W |
| Romania | RO | 10YRO-TEL------P |
| Slovakia | SK | 10YSK-SEPS-----K |
| Slovenia | SI | 10YSI-ELES-----O |
| Spain | ES | 10YES-REE------0 |
| Sweden | SE | 10YSE-1--------K |
| Switzerland | CH | 10YCH-SWISSGRIDZ |
| United Kingdom | GB | 10YGB----------A |

## Setup

### Prerequisites

1. **ENTSO-E API Key**: 
   - Register at [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
   - Email transparency@entsoe.eu with subject "Restful API access"
   - Generate API key from account settings after approval

2. **Elasticsearch Cloud**:
   - Active Elasticsearch deployment
   - Cloud ID and API key with write permissions

### Configuration

Configure environment variables in `local.settings.json`:

```json
{
  "Values": {
    "ELASTICSEARCH_CLOUD_ID": "your-elastic-cloud-id",
    "ELASTICSEARCH_API_KEY": "your-elastic-api-key",
    "ENTSOE_API_KEY": "your-entsoe-api-key"
  }
}
```

For Azure deployment, set these as Application Settings.

### Installation

```bash
cd entsoe-function
pip install -r requirements.txt
```

## Usage

### Local Development

Start the function locally:

```bash
func start
```

### Manual Trigger

Trigger data ingestion via HTTP:

```bash
# Ingest all countries
curl http://localhost:7071/api/ingest

# Ingest specific countries
curl "http://localhost:7071/api/ingest?countries=DE,FR,ES"

# POST with JSON body
curl -X POST http://localhost:7071/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"countries": ["DE", "FR", "ES"]}'
```

### Automatic Schedule

The function runs automatically every hour via timer trigger:
- Schedule: `0 0 * * * *` (top of every hour)
- Processes all configured countries
- Stores data in `entsoe-energy` index

## Elasticsearch Index

### Index Name
`entsoe-energy`

### Document Structure

```json
{
  "@timestamp": "2026-01-14T22:00:00.000Z",
  "datetime_from": "2026-01-14T21:00:00.000Z",
  "datetime_to": "2026-01-14T22:00:00.000Z",
  "country_code": "DE",
  "country_name": "Germany",
  "area_code": "10Y1001A1001A83F",
  "location": {
    "lat": 51.1657,
    "lon": 10.4515
  },
  "generation_mix": {
    "wind_onshore": 32.5,
    "solar": 15.2,
    "nuclear": 12.8,
    "fossil_gas": 18.3,
    "fossil_coal": 10.5,
    "biomass": 8.7,
    "hydro_run_of_river": 2.0
  },
  "total_load_mw": 58234.5,
  "carbon_intensity": 285.4,
  "renewable_percentage": 49.7,
  "fossil_percentage": 28.8,
  "low_carbon_percentage": 62.5,
  "data_source": "entsoe.eu",
  "updated_at": "2026-01-14T22:00:00.000Z"
}
```

### Index Mapping

Create the index with proper mapping:

```json
PUT entsoe-energy
{
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "datetime_from": { "type": "date" },
      "datetime_to": { "type": "date" },
      "country_code": { "type": "keyword" },
      "country_name": { "type": "keyword" },
      "area_code": { "type": "keyword" },
      "location": { "type": "geo_point" },
      "generation_mix": { "type": "object" },
      "total_load_mw": { "type": "float" },
      "carbon_intensity": { "type": "float" },
      "renewable_percentage": { "type": "float" },
      "fossil_percentage": { "type": "float" },
      "low_carbon_percentage": { "type": "float" },
      "data_source": { "type": "keyword" },
      "updated_at": { "type": "date" }
    }
  }
}
```

## Dashboard Creation

### Recommended Visualizations

1. **European Energy Map**
   - Visualization: Region Map
   - Field: `location`
   - Metrics: `carbon_intensity`, `renewable_percentage`
   - Shows real-time carbon intensity across Europe

2. **Generation Mix by Country**
   - Visualization: Stacked Bar Chart
   - X-axis: `country_name`
   - Y-axis: Percentage
   - Breakdown: `generation_mix.*`

3. **Carbon Intensity Timeline**
   - Visualization: Line Chart
   - X-axis: `@timestamp`
   - Y-axis: `carbon_intensity`
   - Split by: `country_name`

4. **Renewable Energy Leaders**
   - Visualization: Bar Chart
   - Y-axis: `country_name`
   - Metrics: Average `renewable_percentage`
   - Sort: Descending

5. **Load vs Generation**
   - Visualization: Dual Axis
   - Primary: `total_load_mw`
   - Secondary: Total generation from `generation_mix`

6. **Fossil Fuel Dependency**
   - Visualization: Pie Chart
   - Slice by: `country_name`
   - Metrics: Average `fossil_percentage`

7. **Low Carbon Progress**
   - Visualization: Gauge
   - Metric: Average `low_carbon_percentage`
   - Ranges: 0-33% (red), 34-66% (yellow), 67-100% (green)

### Sample Kibana Dashboard Queries

**Top 5 Countries by Renewable Energy:**
```json
{
  "aggs": {
    "countries": {
      "terms": {
        "field": "country_name",
        "size": 5,
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

**Carbon Intensity Heatmap:**
```json
{
  "aggs": {
    "time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "1h"
      },
      "aggs": {
        "countries": {
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

## Energy Source Codes

The function maps ENTSO-E production type codes to readable names:

| Code | Energy Source |
|------|---------------|
| B01 | Biomass |
| B02 | Fossil Brown Coal |
| B03 | Fossil Coal |
| B04 | Fossil Gas |
| B05 | Fossil Hard Coal |
| B06 | Fossil Oil |
| B09 | Geothermal |
| B10 | Hydro Pumped Storage |
| B11 | Hydro Run-of-River |
| B12 | Hydro Water Reservoir |
| B13 | Marine |
| B14 | Nuclear |
| B15 | Other Renewable |
| B16 | Solar |
| B17 | Waste |
| B18 | Wind Offshore |
| B19 | Wind Onshore |
| B20 | Other |

## Carbon Intensity Calculation

The function calculates carbon intensity using these emission factors (gCO2/kWh):

- **Coal**: 820 gCO2/kWh
- **Gas**: 490 gCO2/kWh
- **Oil**: 650 gCO2/kWh
- **Nuclear**: 12 gCO2/kWh
- **Wind**: 11-12 gCO2/kWh
- **Solar**: 45 gCO2/kWh
- **Hydro**: 24 gCO2/kWh
- **Biomass**: 230 gCO2/kWh

Formula: `Σ (generation_percentage × emission_factor)`

## Troubleshooting

### Common Issues

**Authentication Errors:**
- Verify ENTSOE_API_KEY is correctly set
- Check API key is active on ENTSO-E portal
- Ensure email confirmation was completed

**Missing Data:**
- Some countries may have data availability issues
- Check ENTSO-E platform status
- Verify country area codes are correct

**Rate Limiting:**
- ENTSO-E API has rate limits
- Function includes 30-second timeout per request
- Consider increasing timer interval if hitting limits

### Logs

View function logs:
```bash
func logs
```

Monitor Elasticsearch ingestion:
```bash
GET entsoe-energy/_search
{
  "size": 0,
  "aggs": {
    "by_country": {
      "terms": { "field": "country_name" }
    }
  }
}
```

## Deployment

### Azure Function App

```bash
# Create function app
az functionapp create \
  --resource-group <resource-group> \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name entsoe-function \
  --storage-account <storage-account>

# Configure app settings
az functionapp config appsettings set \
  --name entsoe-function \
  --resource-group <resource-group> \
  --settings \
    ELASTICSEARCH_CLOUD_ID=<your-cloud-id> \
    ELASTICSEARCH_API_KEY=<your-api-key> \
    ENTSOE_API_KEY=<your-entsoe-key>

# Deploy
func azure functionapp publish entsoe-function
```

## API Documentation

- **ENTSO-E API**: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
- **Postman Collection**: https://documenter.getpostman.com/view/7009892/2s93JtP3F6
- **Data Manual**: https://www.entsoe.eu/data/entso-e-transparency-platform/Manual-of-Procedures/

## License

Same as parent repository.
