#!/bin/bash

# Automated test script for the demo

set -e

echo "================================================"
echo "Cloud Cost & Sustainability Demo - Test Suite"
echo "================================================"
echo ""

PASSED=0
FAILED=0

function test_passed {
    echo "✓ $1"
    PASSED=$((PASSED + 1))
}

function test_failed {
    echo "✗ $1"
    FAILED=$((FAILED + 1))
}

# Test 1: Python availability
echo "Test 1: Checking Python..."
if python3 --version > /dev/null 2>&1; then
    test_passed "Python 3 is installed"
else
    test_failed "Python 3 is not installed"
    exit 1
fi

# Test 2: Docker availability
echo "Test 2: Checking Docker..."
if docker --version > /dev/null 2>&1; then
    test_passed "Docker is installed"
else
    test_failed "Docker is not installed"
    exit 1
fi

# Test 3: Docker Compose availability
echo "Test 3: Checking Docker Compose..."
if docker compose version > /dev/null 2>&1; then
    test_passed "Docker Compose is available"
else
    test_failed "Docker Compose is not available"
    exit 1
fi

# Test 4: Generate data
echo "Test 4: Generating mock data..."
if python3 scripts/generate_cost_data.py > /dev/null 2>&1; then
    if [ -f data/cloud-costs.csv ]; then
        lines=$(wc -l < data/cloud-costs.csv)
        if [ "$lines" -gt 100 ]; then
            test_passed "Generated $lines lines of cost data"
        else
            test_failed "Generated only $lines lines of data"
        fi
    else
        test_failed "CSV file was not created"
    fi
else
    test_failed "Data generation script failed"
fi

# Test 5: Validate CSV structure
echo "Test 5: Validating CSV structure..."
if python3 << 'PYEOF'
import csv
import sys

try:
    with open('data/cloud-costs.csv', 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        expected = ['timestamp', 'service', 'region', 'cost', 'provider',
                   'carbon_intensity', 'carbon_emissions_g', 'usage_hours',
                   'environment', 'is_anomaly']
        
        if headers != expected:
            print(f"Headers mismatch", file=sys.stderr)
            sys.exit(1)
        
        # Read first record
        record = next(reader)
        
        # Validate types
        float(record['cost'])
        int(record['carbon_intensity'])
        float(record['carbon_emissions_g'])
        float(record['usage_hours'])
        
        sys.exit(0)
except Exception as e:
    print(f"Validation error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
then
    test_passed "CSV structure is valid"
else
    test_failed "CSV structure validation failed"
fi

# Test 6: Validate Docker Compose config
echo "Test 6: Validating Docker Compose configuration..."
if docker compose config > /dev/null 2>&1; then
    test_passed "docker-compose.yml is valid"
else
    test_failed "docker-compose.yml has errors"
fi

# Test 7: Validate Filebeat config
echo "Test 7: Validating Filebeat configuration..."
if python3 -c "import yaml; yaml.safe_load(open('filebeat/filebeat.yml'))" > /dev/null 2>&1; then
    test_passed "filebeat.yml is valid YAML"
else
    test_failed "filebeat.yml has YAML errors"
fi

# Test 8: Validate Elasticsearch template
echo "Test 8: Validating Elasticsearch index template..."
if python3 -c "import json; json.load(open('elasticsearch/index-template.json'))" > /dev/null 2>&1; then
    test_passed "index-template.json is valid JSON"
else
    test_failed "index-template.json has JSON errors"
fi

# Test 9: Validate Kibana dashboard
echo "Test 9: Validating Kibana dashboard..."
if python3 << 'PYEOF'
import json
import sys

try:
    with open('kibana/dashboards/cost-sustainability.ndjson', 'r') as f:
        line_count = 0
        for line in f:
            if line.strip():
                json.loads(line)
                line_count += 1
        
        if line_count < 5:  # Should have at least 5 objects
            print(f"Only {line_count} objects in NDJSON", file=sys.stderr)
            sys.exit(1)
        
        sys.exit(0)
except Exception as e:
    print(f"NDJSON error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
then
    test_passed "cost-sustainability.ndjson is valid"
else
    test_failed "cost-sustainability.ndjson has errors"
fi

# Test 10: Check file permissions
echo "Test 10: Checking file permissions..."
if [ -x setup.sh ]; then
    test_passed "setup.sh is executable"
else
    test_failed "setup.sh is not executable"
fi

# Summary
echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "All tests passed! ✓"
    echo ""
    echo "You can now run the demo with:"
    echo "  ./setup.sh"
    exit 0
else
    echo "Some tests failed. Please fix the issues before running the demo."
    exit 1
fi
