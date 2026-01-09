# Testing Guide

This document describes how to test the Cloud Cost & Sustainability Demo.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ installed
- At least 4GB of available RAM for Docker
- Ports 9200, 5601 available

## Quick Test

Run the automated setup script:

```bash
./setup.sh
```

This will:
1. Generate mock cost data
2. Start all Docker containers
3. Wait for services to be ready
4. Display access instructions

## Manual Testing Steps

### 1. Generate Test Data

```bash
python3 scripts/generate_cost_data.py
```

**Expected Output:**
- Creates `data/cloud-costs.csv`
- Reports ~2400 records for 90 days
- Shows total cost and carbon emissions summary
- Reports 5-10% anomaly days

**Validation:**
```bash
# Check file exists
ls -lh data/cloud-costs.csv

# Check record count
wc -l data/cloud-costs.csv

# View sample data
head -5 data/cloud-costs.csv
```

### 2. Validate Configurations

```bash
# Validate Docker Compose
docker compose config

# Validate Filebeat YAML
python3 -c "import yaml; yaml.safe_load(open('filebeat/filebeat.yml'))"

# Validate Elasticsearch template
python3 -c "import json; json.load(open('elasticsearch/index-template.json'))"

# Validate Kibana dashboard
python3 -c "
import json
with open('kibana/dashboards/cost-sustainability.ndjson', 'r') as f:
    for line in f:
        if line.strip():
            json.loads(line)
"
```

### 3. Start Services

```bash
docker compose up -d
```

**Expected Output:**
- Creates and starts 3 containers: elasticsearch, kibana, filebeat
- All services should be in "running" state

**Validation:**
```bash
# Check container status
docker compose ps

# All should show "Up" status
```

### 4. Wait for Services

```bash
# Wait for Elasticsearch (may take 1-2 minutes)
until curl -u elastic:changeme -f http://localhost:9200/_cluster/health 2>/dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 10
done

# Wait for Kibana (may take 2-3 minutes)
until curl -f http://localhost:5601/api/status 2>/dev/null; do
    echo "Waiting for Kibana..."
    sleep 10
done
```

### 5. Verify Data Ingestion

```bash
# Check if index was created (wait a few minutes after filebeat starts)
curl -u elastic:changeme "http://localhost:9200/_cat/indices/cloud-costs-*?v"

# Check document count
curl -u elastic:changeme "http://localhost:9200/cloud-costs-*/_count?pretty"

# Sample documents
curl -u elastic:changeme "http://localhost:9200/cloud-costs-*/_search?size=2&pretty"
```

**Expected Results:**
- Index `cloud-costs-YYYY.MM` exists
- Document count should be ~2400
- Documents contain all expected fields

### 6. Test Kibana Access

```bash
# Check Kibana is accessible
curl -f http://localhost:5601/api/status
```

**Browser Test:**
1. Open http://localhost:5601
2. Login with `elastic` / `changeme`
3. Should see Kibana home page

### 7. Create Index Pattern

**In Kibana UI:**
1. Go to Stack Management → Index Patterns
2. Click "Create index pattern"
3. Enter: `cloud-costs-*`
4. Click "Next step"
5. Select `@timestamp` as time field
6. Click "Create index pattern"

**Validation:**
- Index pattern shows in the list
- Field list includes: cost, service, region, provider, carbon_intensity, etc.

### 8. Import Dashboard

**In Kibana UI:**
1. Go to Stack Management → Saved Objects
2. Click "Import"
3. Select `kibana/dashboards/cost-sustainability.ndjson`
4. If conflicts appear, choose "Overwrite"
5. Click "Import"

**Validation:**
- Import successful message appears
- No errors reported

### 9. View Dashboard

**In Kibana UI:**
1. Go to Analytics → Dashboard
2. Find "Cloud Cost & Sustainability Dashboard"
3. Click to open

**Expected Visualizations:**
1. ✓ Total Cost Over Time (line chart)
2. ✓ Cost by Service (pie chart)
3. ✓ Cost by Region (bar chart)
4. ✓ Cost by Environment (pie chart)
5. ✓ Cost by Provider (stacked histogram)
6. ✓ Carbon Intensity by Region (bar chart)
7. ✓ Carbon Emissions Over Time (area chart)
8. ✓ Anomaly Days (table)

**Validation Checks:**
- All 8 visualizations display data
- No error messages
- Charts show realistic patterns:
  - Total costs trend over 90 days
  - EC2/Virtual Machines highest cost
  - Production environment highest
  - Carbon intensity varies by region
  - Anomaly days highlighted in table

### 10. Test Filtering

**In Dashboard:**
1. Click on a service in the pie chart (e.g., "EC2")
   - All charts should filter to that service
2. Click on a region
   - Should filter to that region
3. Clear filters
   - All data returns

### 11. Test Time Range

**In Dashboard:**
1. Change time range to "Last 30 days"
   - Data should filter appropriately
2. Try "Last 7 days"
   - Should show recent week
3. Try custom range
   - Should work correctly

## Troubleshooting

### Elasticsearch won't start

```bash
# Check logs
docker compose logs elasticsearch

# Common issues:
# - Not enough memory: Increase Docker memory to 4GB+
# - Port in use: Change port in docker-compose.yml
```

### Kibana won't connect

```bash
# Check logs
docker compose logs kibana

# Verify Elasticsearch is running
curl -u elastic:changeme http://localhost:9200
```

### Filebeat not ingesting

```bash
# Check logs
docker compose logs filebeat

# Common issues:
# - CSV file path wrong: Check volume mount
# - Permission issues: Check file permissions
# - Elasticsearch connection: Verify ES is running
```

### No data in index

```bash
# Check filebeat logs for errors
docker compose logs filebeat | grep -i error

# Verify CSV file exists
ls -lh data/cloud-costs.csv

# Check filebeat registry
docker compose exec filebeat ls -la /usr/share/filebeat/data/registry
```

### Dashboard visualizations empty

1. Verify index pattern created correctly
2. Check time range (must include data dates)
3. Verify documents in Elasticsearch
4. Check for filter pills at top of dashboard

## Performance Testing

### Index Performance

```bash
# Time to index all documents
time docker compose logs filebeat | grep "events have been published"
```

**Expected:** Should complete within 1-2 minutes

### Query Performance

In Kibana Dev Tools:

```json
# Test aggregation query
GET cloud-costs-*/_search
{
  "size": 0,
  "aggs": {
    "total_cost": {
      "sum": {
        "field": "cost"
      }
    },
    "by_service": {
      "terms": {
        "field": "service",
        "size": 20
      },
      "aggs": {
        "cost": {
          "sum": {
            "field": "cost"
          }
        }
      }
    }
  }
}
```

**Expected:** Query completes in < 100ms

## Cleanup

```bash
# Stop services
docker compose down

# Remove volumes (deletes all data)
docker compose down -v

# Remove generated data
rm data/cloud-costs.csv
```

## Automated Test Script

```bash
#!/bin/bash

echo "Running automated tests..."

# Test 1: Generate data
echo "Test 1: Generating data..."
python3 scripts/generate_cost_data.py > /dev/null 2>&1
if [ -f data/cloud-costs.csv ]; then
    echo "✓ Data generation passed"
else
    echo "✗ Data generation failed"
    exit 1
fi

# Test 2: Validate configs
echo "Test 2: Validating configurations..."
docker compose config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Configuration validation passed"
else
    echo "✗ Configuration validation failed"
    exit 1
fi

# Test 3: Start services
echo "Test 3: Starting services..."
docker compose up -d > /dev/null 2>&1
sleep 120  # Wait for services

# Test 4: Check Elasticsearch
echo "Test 4: Checking Elasticsearch..."
response=$(curl -s -o /dev/null -w "%{http_code}" -u elastic:changeme http://localhost:9200)
if [ "$response" = "200" ]; then
    echo "✓ Elasticsearch health check passed"
else
    echo "✗ Elasticsearch health check failed (HTTP $response)"
    docker compose down
    exit 1
fi

# Test 5: Check Kibana
echo "Test 5: Checking Kibana..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5601/api/status)
if [ "$response" = "200" ]; then
    echo "✓ Kibana health check passed"
else
    echo "✗ Kibana health check failed (HTTP $response)"
    docker compose down
    exit 1
fi

# Test 6: Check data ingestion (wait a bit more)
echo "Test 6: Checking data ingestion..."
sleep 60
count=$(curl -s -u elastic:changeme "http://localhost:9200/cloud-costs-*/_count" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
if [ "$count" -gt 100 ]; then
    echo "✓ Data ingestion passed ($count documents)"
else
    echo "✗ Data ingestion failed (only $count documents)"
    docker compose down
    exit 1
fi

echo ""
echo "All tests passed! ✓"
echo "Access Kibana at: http://localhost:5601"
echo "Username: elastic"
echo "Password: changeme"

# Optional: cleanup
# docker compose down
```

Save this as `test.sh` and run with `bash test.sh`

## Success Criteria

The demo is working correctly when:

- ✓ All Docker containers start and stay running
- ✓ Elasticsearch cluster health is green/yellow
- ✓ Kibana is accessible at http://localhost:5601
- ✓ ~2400 cost documents are indexed
- ✓ Index pattern `cloud-costs-*` is created
- ✓ Dashboard imports without errors
- ✓ All 8 visualizations display data
- ✓ Filters and time range work correctly
- ✓ Anomaly days are identified in the data
- ✓ Carbon intensity varies by region as expected

## Reporting Issues

When reporting issues, include:

1. Docker version: `docker --version`
2. Docker Compose version: `docker compose version`
3. Python version: `python3 --version`
4. OS and architecture
5. Container logs: `docker compose logs`
6. Error messages
7. Steps to reproduce
