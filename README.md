# Elastic Cloud Cost & Sustainability Demo

A demonstration of how Elastic Stack can support cost visibility and sustainability discussions for cloud infrastructure, going beyond traditional log analysis.

## Overview

This demo showcases:
- **Cost per service** - Visualize spending across different cloud services
- **Cost trend over time** - Track spending patterns and identify trends
- **Anomaly detection** - Identify unusual spending days
- **Carbon intensity tracking** - Monitor environmental impact by region

## What Makes This Demo Stand Out

✔ **Business relevance** - Addresses real FinOps challenges  
✔ **Not the usual "log dashboard"** - Focuses on cost and sustainability metrics  
✔ **Opens discussion on FinOps + Green IT** - Bridges technical and business stakeholders

## Architecture

```
Mock Cost Data (CSV) 
    → Filebeat (CSV ingestion)
    → Elasticsearch (indexing & storage)
    → Kibana (visualization & dashboards)
```

## Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for data generation)

## Quick Start

1. **Generate mock cost data:**
   ```bash
   python scripts/generate_cost_data.py
   ```

2. **Start the Elastic Stack:**
   ```bash
   docker-compose up -d
   ```

3. **Access Kibana:**
   - URL: http://localhost:5601
   - Username: elastic
   - Password: changeme

4. **Import dashboards:**
   - Navigate to Stack Management → Saved Objects
   - Import the dashboard from `kibana/dashboards/cost-sustainability.ndjson`

## Data Structure

The mock cost data includes:
- **timestamp** - Date of the cost entry
- **service** - Cloud service name (EC2, S3, RDS, Lambda, etc.)
- **region** - AWS/Azure region
- **cost** - Daily cost in USD
- **provider** - Cloud provider (AWS/Azure)
- **carbon_intensity** - Carbon intensity (gCO2/kWh) for the region
- **usage_hours** - Hours of service usage
- **environment** - Environment tag (production/staging/development)

## Dashboards

### Cost Overview Dashboard
- Total spending trends
- Cost breakdown by service
- Regional cost distribution
- Carbon emissions tracking

### Anomaly Detection
- Days with unusual spending patterns
- Service-level anomalies
- Alert thresholds

## Project Structure

```
.
├── data/                       # Generated cost data
│   └── cloud-costs.csv
├── filebeat/                   # Filebeat configuration
│   └── filebeat.yml
├── elasticsearch/              # Elasticsearch configuration
│   └── index-template.json
├── kibana/                     # Kibana dashboards
│   └── dashboards/
│       └── cost-sustainability.ndjson
├── scripts/                    # Data generation scripts
│   └── generate_cost_data.py
├── docker-compose.yml          # Docker compose setup
└── README.md
```

## Use Cases

1. **FinOps Teams** - Track and optimize cloud spending
2. **Sustainability Officers** - Monitor carbon footprint
3. **Engineering Teams** - Understand cost impact of services
4. **Executive Reporting** - High-level cost trends and insights

## Extending the Demo

- Connect to real AWS Cost Explorer or Azure Cost Management APIs
- Add budget alerts and forecasting
- Integrate with carbon accounting platforms
- Add cost allocation by teams or projects

## License

Apache 2.0 - See LICENSE file