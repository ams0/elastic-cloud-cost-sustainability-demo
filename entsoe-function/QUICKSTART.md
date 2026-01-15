# ENTSO-E Function Quick Start Guide

Get the ENTSO-E Azure Function up and running in 5 minutes!

## Prerequisites

1. ✅ Python 3.9+ installed
2. ✅ Azure Functions Core Tools v4
3. ✅ ENTSO-E API key (see below)
4. ✅ Elasticsearch Cloud deployment

## Step 1: Get Your ENTSO-E API Key

1. Register at https://transparency.entsoe.eu/
2. Email transparency@entsoe.eu with:
   - Subject: "Restful API access"
   - Body: Your registered email address
3. Wait for approval (usually 1-2 business days)
4. Generate token from: Account Settings → Web API Security Token

## Step 2: Configure the Function

Edit `local.settings.json`:

```json
{
  "Values": {
    "ELASTICSEARCH_CLOUD_ID": "your-actual-cloud-id",
    "ELASTICSEARCH_API_KEY": "your-actual-api-key",
    "ENTSOE_API_KEY": "your-actual-entsoe-key"
  }
}
```

## Step 3: Setup Elasticsearch Index

In Kibana Dev Tools, run:

```json
PUT entsoe-energy
{
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "country_code": { "type": "keyword" },
      "country_name": { "type": "keyword" },
      "location": { "type": "geo_point" },
      "carbon_intensity": { "type": "float" },
      "renewable_percentage": { "type": "float" },
      "total_load_mw": { "type": "float" },
      "generation_mix": { "type": "object" }
    }
  }
}
```

## Step 4: Install and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the function locally
func start
```

## Step 5: Test the Function

In another terminal:

```bash
# Test all countries
curl http://localhost:7071/api/ingest

# Test specific countries
curl 'http://localhost:7071/api/ingest?countries=DE,FR,ES'
```

## Step 6: Verify Data in Elasticsearch

In Kibana Dev Tools:

```json
GET entsoe-energy/_search
{
  "size": 5,
  "sort": [{ "@timestamp": "desc" }]
}
```

## Step 7: Create Kibana Dashboard

### Create Index Pattern
1. Stack Management → Index Patterns
2. Create pattern: `entsoe-energy*`
3. Time field: `@timestamp`

### Add Visualizations

**Map Visualization:**
- Type: Region Map
- Metric: Average `carbon_intensity`
- Bucket: Terms on `country_name`

**Bar Chart:**
- Type: Horizontal Bar
- Y-axis: `country_name`
- Metric: Average `renewable_percentage`

**Line Chart:**
- Type: Line
- X-axis: `@timestamp`
- Y-axis: Average `carbon_intensity`
- Split: `country_name`

## Troubleshooting

### "ENTSOE_API_KEY not configured"
→ Check your `local.settings.json` file has the correct key

### "Authentication failed"
→ Verify your ENTSO-E API key is active on the portal

### "No data in Elasticsearch"
→ Check function logs with `func logs`
→ Verify Elasticsearch credentials are correct

### Function times out
→ Reduce countries with `?countries=DE,FR`
→ ENTSO-E API can be slow for some countries

## Next Steps

1. **Deploy to Azure**:
   ```bash
   func azure functionapp publish <your-function-app-name>
   ```

2. **Schedule Automatic Runs**:
   - Already configured: Runs every hour
   - Modify in `function_app.py`: `@app.timer_trigger(schedule="...")`

3. **Build Advanced Dashboards**:
   - See `ELASTICSEARCH_SETUP.md` for query examples
   - See `README.md` for visualization ideas

4. **Combine with UK Data**:
   - Run both `entsoe-function` and `electricity-maps-function`
   - See `COMPARISON.md` for integration strategies

## Countries Supported

🇦🇹 Austria, 🇧🇪 Belgium, 🇧🇬 Bulgaria, 🇭�� Croatia, 🇨🇿 Czech Republic, 🇩🇰 Denmark, 🇪🇪 Estonia, 🇫🇮 Finland, 🇫🇷 France, 🇩🇪 Germany, 🇬🇷 Greece, 🇭🇺 Hungary, 🇮🇪 Ireland, 🇮🇹 Italy, 🇱🇻 Latvia, 🇱🇹 Lithuania, 🇱🇺 Luxembourg, 🇳🇱 Netherlands, 🇳🇴 Norway, 🇵🇱 Poland, 🇵🇹 Portugal, 🇷🇴 Romania, 🇸🇰 Slovakia, 🇸🇮 Slovenia, 🇪🇸 Spain, 🇸🇪 Sweden, 🇨🇭 Switzerland, 🇬🇧 United Kingdom

## Support

- ENTSO-E API Docs: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
- Elasticsearch Docs: https://www.elastic.co/guide/
- Azure Functions Docs: https://docs.microsoft.com/azure/azure-functions/

Happy energy data monitoring! 🌍⚡
