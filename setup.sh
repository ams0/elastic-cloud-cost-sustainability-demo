#!/bin/bash

# Setup script for Elastic Cloud Cost & Sustainability Demo

echo "================================================"
echo "Elastic Cloud Cost & Sustainability Demo Setup"
echo "================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "Step 1: Generating mock cost data..."
python3 scripts/generate_cost_data.py
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate cost data"
    exit 1
fi
echo "✓ Cost data generated successfully"
echo ""

echo "Step 2: Starting Elastic Stack with Docker Compose..."
docker compose up -d
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Docker containers"
    exit 1
fi
echo "✓ Docker containers started"
echo ""

echo "Step 3: Waiting for services to be ready..."
echo "This may take a few minutes..."

# Wait for Elasticsearch
echo -n "Waiting for Elasticsearch..."
max_attempts=30
attempt=0
until curl -u elastic:changeme -f http://localhost:9200/_cluster/health 2>/dev/null | grep -q "status"; do
    attempt=$((attempt+1))
    if [ $attempt -eq $max_attempts ]; then
        echo " timeout!"
        echo "Error: Elasticsearch failed to start"
        exit 1
    fi
    echo -n "."
    sleep 10
done
echo " ready!"

# Wait for Kibana
echo -n "Waiting for Kibana..."
attempt=0
until curl -f http://localhost:5601/api/status 2>/dev/null | grep -q "available"; do
    attempt=$((attempt+1))
    if [ $attempt -eq $max_attempts ]; then
        echo " timeout!"
        echo "Error: Kibana failed to start"
        exit 1
    fi
    echo -n "."
    sleep 10
done
echo " ready!"

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Access Kibana at: http://localhost:5601"
echo "Username: elastic"
echo "Password: changeme"
echo ""
echo "Next steps:"
echo "1. Wait a few minutes for Filebeat to ingest the data"
echo "2. Go to Stack Management → Index Patterns"
echo "3. Create index pattern: cloud-costs-*"
echo "4. Set time field: @timestamp"
echo "5. Go to Stack Management → Saved Objects"
echo "6. Import: kibana/dashboards/cost-sustainability.ndjson"
echo "7. View the dashboard under Analytics → Dashboard"
echo ""
echo "To stop the demo:"
echo "  docker compose down"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
