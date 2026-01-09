#!/usr/bin/env python3
"""
Generate mock cloud cost data with carbon intensity for sustainability tracking.

This script creates realistic cost data for AWS and Azure services with:
- Daily cost entries
- Multiple services (compute, storage, database, etc.)
- Regional distribution
- Carbon intensity per region
- Occasional anomalies for demonstration
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Carbon intensity data (gCO2/kWh) - based on real regional grid data
CARBON_INTENSITY = {
    # AWS Regions
    'us-east-1': 415,      # Virginia - US grid average
    'us-west-2': 285,      # Oregon - cleaner hydropower
    'eu-west-1': 325,      # Ireland - wind power
    'eu-central-1': 485,   # Frankfurt - higher carbon grid
    'ap-southeast-1': 520, # Singapore - high carbon
    'ap-northeast-1': 510, # Tokyo - fossil fuel dependent
    'ca-central-1': 150,   # Canada - hydropower
    'sa-east-1': 95,       # São Paulo - hydropower
    
    # Azure Regions
    'eastus': 415,
    'westus2': 285,
    'northeurope': 325,
    'westeurope': 390,
    'southeastasia': 520,
    'japaneast': 510,
    'canadacentral': 150,
    'brazilsouth': 95,
}

# Cloud services with typical cost characteristics
SERVICES = {
    # AWS Services
    'EC2': {'provider': 'AWS', 'base_cost': 850, 'variance': 200, 'regions': ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1']},
    'S3': {'provider': 'AWS', 'base_cost': 320, 'variance': 80, 'regions': ['us-east-1', 'us-west-2', 'eu-west-1']},
    'RDS': {'provider': 'AWS', 'base_cost': 560, 'variance': 120, 'regions': ['us-east-1', 'eu-west-1']},
    'Lambda': {'provider': 'AWS', 'base_cost': 145, 'variance': 60, 'regions': ['us-east-1', 'us-west-2', 'ap-southeast-1']},
    'CloudFront': {'provider': 'AWS', 'base_cost': 230, 'variance': 50, 'regions': ['us-east-1']},
    'DynamoDB': {'provider': 'AWS', 'base_cost': 180, 'variance': 40, 'regions': ['us-east-1', 'ap-northeast-1']},
    'EBS': {'provider': 'AWS', 'base_cost': 290, 'variance': 70, 'regions': ['us-east-1', 'us-west-2', 'eu-west-1']},
    'VPC': {'provider': 'AWS', 'base_cost': 85, 'variance': 20, 'regions': ['us-east-1', 'us-west-2']},
    
    # Azure Services
    'Virtual Machines': {'provider': 'Azure', 'base_cost': 920, 'variance': 250, 'regions': ['eastus', 'westus2', 'northeurope']},
    'Blob Storage': {'provider': 'Azure', 'base_cost': 280, 'variance': 70, 'regions': ['eastus', 'westus2', 'westeurope']},
    'SQL Database': {'provider': 'Azure', 'base_cost': 640, 'variance': 150, 'regions': ['eastus', 'northeurope']},
    'Functions': {'provider': 'Azure', 'base_cost': 125, 'variance': 50, 'regions': ['eastus', 'westus2']},
    'CDN': {'provider': 'Azure', 'base_cost': 195, 'variance': 45, 'regions': ['eastus']},
    'Cosmos DB': {'provider': 'Azure', 'base_cost': 420, 'variance': 100, 'regions': ['eastus', 'southeastasia']},
}

ENVIRONMENTS = ['production', 'staging', 'development']

def generate_cost_data(days=90, output_file='data/cloud-costs.csv'):
    """Generate mock cost data for the specified number of days."""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Create output directory if it doesn't exist
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    records = []
    
    # Generate data for each day
    current_date = start_date
    while current_date <= end_date:
        
        # Check if this is an anomaly day (5% chance)
        is_anomaly_day = random.random() < 0.05
        anomaly_multiplier = random.uniform(2.0, 4.0) if is_anomaly_day else 1.0
        
        # Generate entries for each service
        for service_name, service_config in SERVICES.items():
            # Each service might have entries in multiple regions
            for region in service_config['regions']:
                # 80% chance of having cost on any given day
                if random.random() < 0.8:
                    # Calculate cost with some random variation
                    base_cost = service_config['base_cost']
                    variance = service_config['variance']
                    
                    # Add weekly pattern (weekends might have lower costs)
                    day_of_week = current_date.weekday()
                    if day_of_week >= 5:  # Weekend
                        day_multiplier = random.uniform(0.6, 0.8)
                    else:
                        day_multiplier = random.uniform(0.9, 1.1)
                    
                    daily_cost = base_cost * day_multiplier
                    cost_variation = random.uniform(-variance, variance)
                    cost = max(0, daily_cost + cost_variation)
                    
                    # Apply anomaly multiplier
                    cost *= anomaly_multiplier
                    
                    # Calculate usage hours (approximate)
                    usage_hours = random.uniform(18, 24) if day_of_week < 5 else random.uniform(12, 20)
                    
                    # Select environment
                    if service_name in ['EC2', 'Virtual Machines', 'RDS', 'SQL Database']:
                        # Production environments for critical services
                        environment = random.choices(
                            ENVIRONMENTS, 
                            weights=[0.6, 0.25, 0.15]
                        )[0]
                    else:
                        environment = random.choice(ENVIRONMENTS)
                    
                    # Calculate carbon emissions (cost correlates with usage)
                    carbon_intensity = CARBON_INTENSITY[region]
                    estimated_kwh = cost / 150  # Rough estimate: $150 per kWh equivalent
                    carbon_emissions = estimated_kwh * carbon_intensity
                    
                    record = {
                        'timestamp': current_date.strftime('%Y-%m-%d'),
                        'service': service_name,
                        'region': region,
                        'cost': round(cost, 2),
                        'provider': service_config['provider'],
                        'carbon_intensity': carbon_intensity,
                        'carbon_emissions_g': round(carbon_emissions, 2),
                        'usage_hours': round(usage_hours, 2),
                        'environment': environment,
                        'is_anomaly': 'yes' if is_anomaly_day else 'no'
                    }
                    
                    records.append(record)
        
        current_date += timedelta(days=1)
    
    # Write to CSV
    fieldnames = [
        'timestamp', 'service', 'region', 'cost', 'provider',
        'carbon_intensity', 'carbon_emissions_g', 'usage_hours',
        'environment', 'is_anomaly'
    ]
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Generated {len(records)} cost records")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Output file: {output_file}")
    
    # Print summary statistics
    total_cost = sum(r['cost'] for r in records)
    total_carbon = sum(r['carbon_emissions_g'] for r in records)
    print(f"\nSummary:")
    print(f"  Total cost: ${total_cost:,.2f}")
    print(f"  Total carbon emissions: {total_carbon:,.2f} gCO2")
    print(f"  Average daily cost: ${total_cost/days:,.2f}")
    print(f"  Number of anomaly days: {sum(1 for r in records if r['is_anomaly'] == 'yes') // len(SERVICES)}")

if __name__ == '__main__':
    generate_cost_data(days=90)
