# Comparison: Electricity Maps vs ENTSO-E Functions

This document compares the two Azure Functions for electricity and carbon intensity data.

## Overview

| Feature | Electricity Maps Function | ENTSO-E Function |
|---------|--------------------------|------------------|
| **Data Source** | UK Carbon Intensity API | ENTSO-E Transparency Platform |
| **Geographic Coverage** | UK only (17 regions) | 28 European countries |
| **API Authentication** | None required | API key required |
| **Update Frequency** | Every 30 minutes | Every hour |
| **Data Granularity** | Regional (UK DNO regions) | National (country-level) |
| **Index Name** | `electricity-maps` | `entsoe-energy` |

## Data Coverage

### Electricity Maps (UK Carbon Intensity)
- **Countries**: United Kingdom only
- **Regions**: 17 DNO (Distribution Network Operator) regions
  - North Scotland, South Scotland
  - North West England, North East England
  - Yorkshire, Wales, London, etc.
- **Coordinates**: Specific lat/lon for each UK region
- **Data**: Regional carbon intensity with national rollup

### ENTSO-E (European Data)
- **Countries**: 28 European countries
  - Western: UK, FR, DE, ES, PT, IT, BE, NL, LU, IE, CH
  - Northern: NO, SE, FI, DK, EE, LV, LT
  - Central: AT, CZ, SK, PL, HU, SI, HR
  - Southern: GR, BG, RO
- **Regions**: Country-level only (no sub-regions)
- **Coordinates**: Country centroids
- **Data**: National generation, load, and carbon intensity

## Data Fields Comparison

### Common Fields (Both Functions)
- `@timestamp`: Event timestamp
- `country`: Country code or name
- `carbon_intensity`: gCO2/kWh
- `generation_mix`: Energy sources breakdown
- `renewable_percentage`: % renewable energy
- `fossil_percentage`: % fossil fuel energy
- `low_carbon_percentage`: % renewable + nuclear
- `data_source`: API source identifier
- `location`: Geographic coordinates

### Electricity Maps Unique Fields
- `region_id`: UK DNO region ID (1-17)
- `region_name`: Short name (e.g., "London")
- `dno_region`: Full DNO name
- `datetime_from`, `datetime_to`: Data validity period
- `carbon_intensity_index`: UK intensity rating (very low, low, moderate, high, very high)

### ENTSO-E Unique Fields
- `country_code`: ISO 2-letter code (DE, FR, etc.)
- `country_name`: Full country name
- `area_code`: ENTSO-E bidding zone code
- `total_load_mw`: Actual total electricity load in MW
- `datetime_from`, `datetime_to`: Data validity period
- More detailed generation mix (18+ fuel types)

## Generation Mix Details

### Electricity Maps (UK API)
Fuel types tracked:
- `biomass`
- `coal`
- `gas`
- `nuclear`
- `hydro`
- `imports`
- `solar`
- `wind`
- `other`

### ENTSO-E
Fuel types tracked (more granular):
- `biomass`
- `fossil_brown_coal`, `fossil_coal`, `fossil_hard_coal`
- `fossil_gas`
- `fossil_oil`
- `geothermal`
- `hydro_pumped_storage`, `hydro_run_of_river`, `hydro_water_reservoir`
- `marine`
- `nuclear`
- `other_renewable`
- `solar`
- `waste`
- `wind_offshore`, `wind_onshore`
- `other`

## API Characteristics

### Electricity Maps (UK Carbon Intensity API)
- **Endpoint**: `https://api.carbonintensity.org.uk/`
- **Authentication**: None
- **Rate Limits**: Generous (no published limit)
- **Response Format**: JSON
- **Data Latency**: Real-time to 30 minutes
- **Historical Data**: Limited (48 hours)
- **Documentation**: https://carbonintensity.org.uk/

### ENTSO-E API
- **Endpoint**: `https://web-api.tp.entsoe.eu/api`
- **Authentication**: API key (security token) required
- **Rate Limits**: 400 requests per minute per IP
- **Response Format**: XML (parsed to JSON)
- **Data Latency**: 15-60 minutes (varies by country)
- **Historical Data**: Extensive (years of data available)
- **Documentation**: https://transparency.entsoe.eu/

## Use Cases

### Use Electricity Maps When:
- ✅ You need UK-specific regional data
- ✅ You want sub-national granularity
- ✅ You don't want to manage API keys
- ✅ You need the UK carbon intensity index
- ✅ You're building UK-focused applications

### Use ENTSO-E When:
- ✅ You need pan-European coverage
- ✅ You want to compare countries
- ✅ You need actual load data (MW)
- ✅ You want detailed generation breakdowns
- ✅ You're building Europe-wide dashboards
- ✅ You need historical European energy data

## Dashboard Recommendations

### Combined Dashboard Ideas

1. **European Overview with UK Detail**
   - Main map: All European countries (ENTSO-E data)
   - Drill-down: UK regions (Electricity Maps data)
   - Comparison: UK vs. rest of Europe

2. **Carbon Intensity Comparison**
   - Line chart: UK regions over time
   - Line chart: European countries over time
   - Highlight: Best/worst performers

3. **Renewable Energy Leaders**
   - Bar chart: Top European countries (ENTSO-E)
   - Bar chart: Top UK regions (Electricity Maps)
   - Metrics: Renewable percentage

4. **Load Analysis** (ENTSO-E only)
   - Europe-wide electricity demand
   - Peak load times by country
   - Load vs. generation capacity

## Performance Considerations

### Electricity Maps Function
- **Execution Time**: ~10-15 seconds for all UK regions
- **API Calls**: 2 per execution (national + regional)
- **Elasticsearch Writes**: ~18 documents per run
- **Cost**: Minimal (API is free)

### ENTSO-E Function
- **Execution Time**: ~5-10 minutes for all 28 countries
- **API Calls**: 56 per execution (2 per country)
- **Elasticsearch Writes**: ~28 documents per run
- **Cost**: API is free, but consider Azure function execution time

## Integration Strategy

### Running Both Functions
Both functions can run simultaneously and complement each other:

1. **Separate Indices**: 
   - `electricity-maps` for UK data
   - `entsoe-energy` for European data

2. **Combined Index** (alternative):
   - Single `energy-data` index
   - Use `data_source` field to distinguish
   - Add `region_level` field: "national" or "regional"

3. **Unified Dashboards**:
   - Use index patterns: `electricity-maps,entsoe-energy`
   - Filter by country or region
   - Combine visualizations

### Avoiding Duplicates
The UK appears in both datasets:
- ENTSO-E: National UK data (country code: GB)
- Electricity Maps: Regional UK data (17 regions)

**Strategy**:
- Keep both for different granularity needs
- In dashboards, clearly label data source
- For UK comparisons, sum regional data or use national data appropriately

## Sample Unified Query

Search across both indices:

```json
GET electricity-maps,entsoe-energy/_search
{
  "size": 0,
  "aggs": {
    "by_data_source": {
      "terms": { "field": "data_source" },
      "aggs": {
        "avg_carbon": {
          "avg": { "field": "carbon_intensity" }
        },
        "avg_renewable": {
          "avg": { "field": "renewable_percentage" }
        }
      }
    }
  }
}
```

## Recommendations

### For Production Use

1. **Run Both Functions** if you need:
   - Pan-European overview
   - UK regional detail
   - Comprehensive coverage

2. **Adjust Schedules**:
   - Electricity Maps: Every 30 min (follows API update)
   - ENTSO-E: Every hour (balance freshness vs. API load)

3. **Monitor Costs**:
   - Azure Function execution time
   - Elasticsearch storage (both indices grow over time)
   - Consider data retention policies

4. **Error Handling**:
   - ENTSO-E: Some countries may have intermittent data
   - Electricity Maps: Very reliable UK-only service
   - Implement alerting for failed ingestions

5. **Dashboard Strategy**:
   - Create separate dashboards for UK and Europe
   - Create combined dashboard with filters
   - Use clear labeling for data sources

## Future Enhancements

### Potential Improvements

1. **Electricity Maps**:
   - Add forecast data (available in API)
   - Historical data ingestion
   - Add generation data (available in API)

2. **ENTSO-E**:
   - Add cross-border flows
   - Add day-ahead prices
   - Add installed capacity data
   - Regional breakdowns (where available)

3. **Both**:
   - Add data quality metrics
   - Implement caching to reduce API calls
   - Add machine learning for predictions
   - Create alerts for unusual patterns

## Conclusion

Both functions serve different but complementary purposes:

- **Electricity Maps**: Best for detailed UK regional analysis
- **ENTSO-E**: Best for European cross-country comparisons

Together, they provide comprehensive coverage of European electricity and carbon data, enabling rich dashboards and analytics for sustainability tracking and energy transition monitoring.
