# Electricity Maps Azure Function

Azure Function app that retrieves real-time electricity data from [Electricity Maps API](https://www.electricitymap.org/) and ingests it into Elastic Cloud for visualization and analysis.

## Features

- ⚡ Real-time carbon intensity data from 100+ zones worldwide
- 🔄 Timer-triggered automatic data collection (hourly)
- 📊 Power generation breakdown by source (renewable, fossil, nuclear)
- 📈 Historical data ingestion support
- 🌍 Multi-zone monitoring with configurable zones
- ✅ Elastic Cloud integration with optimized indexing

## Prerequisites

- Python 3.9+
- Azure Functions Core Tools v4
- Electricity Maps API key (get it from [Electricity Maps](https://api-portal.electricitymap.org/))
- Elastic Cloud deployment with:
  - Cloud ID
  - API key

## Project Structure

```
electricity-maps-function/
├── function_app.py          # Main function logic
├── requirements.txt         # Python dependencies
├── host.json               # Function host configuration
├── local.settings.json     # Local environment variables (not committed)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Setup

### 1. Install Dependencies

```bash
cd electricity-maps-function
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `local.settings.json` with your credentials:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "ELECTRICITY_MAPS_API_KEY": "your-electricity-maps-api-key",
    "ELASTICSEARCH_CLOUD_ID": "your-elastic-cloud-id",
    "ELASTICSEARCH_API_KEY": "your-elastic-api-key"
  }
}
```

### 3. Run Locally

```bash
func start
```

The function will be available at:
- Timer trigger: Runs automatically every hour
- HTTP trigger (latest): `http://localhost:7071/api/ingest`
- HTTP trigger (history): `http://localhost:7071/api/ingest-history`

## API Endpoints

### Latest Data Ingestion

**Endpoint:** `GET/POST /api/ingest`

Fetch and ingest latest carbon intensity and power breakdown data.

**Query Parameters:**
- `zones` (optional): Comma-separated list of zone codes (e.g., `GB,DE,FR`)

**Example:**
```bash
# Ingest default zones
curl http://localhost:7071/api/ingest

# Ingest specific zones
curl "http://localhost:7071/api/ingest?zones=GB,DE,FR,US-CAL-CISO"
```

**Response:**
```json
{
  "indexed": 10,
  "total": 10,
  "errors": [],
  "results": [
    {
      "zone": "GB",
      "status": "ok",
      "carbon_intensity": 245,
      "renewable_percentage": 42.5
    }
  ]
}
```

### Historical Data Ingestion

**Endpoint:** `GET/POST /api/ingest-history`

Fetch and ingest historical carbon intensity data.

**Query Parameters:**
- `zone` (optional, default: `GB`): Zone code
- `hours` (optional, default: `24`): Hours of historical data to fetch

**Example:**
```bash
# Ingest 24 hours of historical data for GB
curl "http://localhost:7071/api/ingest-history?zone=GB&hours=24"

# Ingest 7 days of historical data for Germany
curl "http://localhost:7071/api/ingest-history?zone=DE&hours=168"
```

**Response:**
```json
{
  "zone": "GB",
  "status": "ok",
  "indexed": 48
}
```

## Supported Zones

Default zones monitored by the timer trigger:

| Zone Code | Region |
|-----------|--------|
| `GB` | Great Britain |
| `DE` | Germany |
| `FR` | France |
| `US-CAL-CISO` | California (CISO) |
| `US-NE-ISNE` | New England (ISO-NE) |
| `US-TEX-ERCO` | Texas (ERCOT) |
| `ES` | Spain |
| `IT-NO` | Italy North |
| `NL` | Netherlands |
| `SE` | Sweden |

For a complete list of available zones, see the [Electricity Maps API documentation](https://api-portal.electricitymap.org/).

## Data Schema

Documents indexed to Elasticsearch include:

```json
{
  "@timestamp": "2024-01-15T10:00:00Z",
  "zone": "GB",
  "carbon_intensity": 245,
  "fossil_free_percentage": 58.3,
  "renewable_percentage": 42.5,
  "power_production_breakdown": {
    "coal": 150.5,
    "gas": 2500.2,
    "nuclear": 5200.0,
    "wind": 8500.5,
    "solar": 1200.3,
    "hydro": 450.0
  },
  "calculated_renewable_percentage": 42.8,
  "calculated_fossil_percentage": 35.2,
  "data_source": "electricitymap.org",
  "updated_at": "2024-01-15T10:05:00Z"
}
```

## Deployment to Azure

### 1. Create Function App

```bash
# Login to Azure
az login

# Create resource group (if needed)
az group create --name electricity-maps-rg --location eastus

# Create storage account
az storage account create \
  --name electricitymapsstorage \
  --resource-group electricity-maps-rg \
  --location eastus \
  --sku Standard_LRS

# Create function app
az functionapp create \
  --resource-group electricity-maps-rg \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name electricity-maps-function \
  --storage-account electricitymapsstorage \
  --os-type Linux
```

### 2. Configure Application Settings

```bash
az functionapp config appsettings set \
  --name electricity-maps-function \
  --resource-group electricity-maps-rg \
  --settings \
    ELECTRICITY_MAPS_API_KEY="your-api-key" \
    ELASTICSEARCH_CLOUD_ID="your-cloud-id" \
    ELASTICSEARCH_API_KEY="your-elastic-api-key"
```

### 3. Deploy Function

```bash
func azure functionapp publish electricity-maps-function
```

## Monitoring

### View Logs

```bash
# Stream logs
func azure functionapp logstream electricity-maps-function

# Or in Azure Portal
# Navigate to: Function App → Monitor → Logs
```

### Application Insights

The function is configured to use Application Insights for monitoring:
- Performance metrics
- Error tracking
- Request counts
- Custom telemetry

## Troubleshooting

### Common Issues

**Issue:** "Authentication failed" when calling Electricity Maps API
- **Solution:** Verify your API key in `local.settings.json` or Azure app settings

**Issue:** "Unable to connect to Elasticsearch"
- **Solution:** Check your Cloud ID and API key. Ensure your IP is whitelisted in Elastic Cloud deployment

**Issue:** "Zone not found"
- **Solution:** Verify the zone code exists in the Electricity Maps API. See [available zones](https://api-portal.electricitymap.org/)

### Debug Mode

Enable detailed logging by setting the log level in `host.json`:

```json
{
  "logging": {
    "logLevel": {
      "default": "Debug"
    }
  }
}
```

## Cost Considerations

- **Electricity Maps API**: Free tier includes 50 API calls/day. Paid plans available.
- **Azure Functions**: Consumption plan charges based on executions and compute time
- **Elastic Cloud**: Charges based on deployment size and data ingestion

**Estimated Costs (hourly timer):**
- API calls: ~720/month (within free tier for most plans)
- Azure Functions: ~$0.50-2.00/month (minimal usage)
- Elastic: Depends on deployment tier

## Security Best Practices

1. **Never commit `local.settings.json`** - It contains sensitive credentials
2. **Use Azure Key Vault** - Store API keys and credentials securely
3. **Enable authentication** - Set `authLevel` to `FUNCTION` or `ADMIN` for HTTP triggers
4. **Restrict CORS** - Configure allowed origins in production
5. **Monitor API usage** - Set up alerts for unusual activity
6. **Rotate keys regularly** - Update API keys and Elastic credentials periodically

## Contributing

To add support for additional zones or features:

1. Update `DEFAULT_ZONES` in `function_app.py`
2. Add any new data processing logic
3. Update this README with new features
4. Test locally before deploying

## Resources

- [Electricity Maps API Documentation](https://api-portal.electricitymap.org/)
- [Azure Functions Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Elastic Cloud Documentation](https://www.elastic.co/guide/en/cloud/current/index.html)

## License

See project root LICENSE file.
