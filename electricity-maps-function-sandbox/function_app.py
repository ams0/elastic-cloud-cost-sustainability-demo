import azure.functions as func
import logging
import requests
from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime

app = func.FunctionApp()

# European zone coordinates for map visualization
ZONE_COORDINATES = {
    "NL": {"lat": 52.3, "lon": 4.9},
    "DE": {"lat": 51.2, "lon": 10.4},
    "FR": {"lat": 46.2, "lon": 2.2},
    "GB": {"lat": 53.5, "lon": -2.5},
    "BE": {"lat": 50.8, "lon": 4.4},
    "ES": {"lat": 40.4, "lon": -3.7},
    "IT": {"lat": 41.9, "lon": 12.5},
    "PT": {"lat": 39.4, "lon": -8.2},
    "AT": {"lat": 47.5, "lon": 14.6},
    "CH": {"lat": 46.8, "lon": 8.2},
    "PL": {"lat": 51.9, "lon": 19.1},
    "CZ": {"lat": 49.8, "lon": 15.5},
    "DK": {"lat": 56.3, "lon": 9.5},
    "SE": {"lat": 60.1, "lon": 18.6},
    "NO": {"lat": 60.5, "lon": 8.5},
    "FI": {"lat": 61.9, "lon": 25.7},
    "IE": {"lat": 53.1, "lon": -7.7},
    "GR": {"lat": 39.1, "lon": 21.8},
    "HU": {"lat": 47.2, "lon": 19.5},
    "RO": {"lat": 45.9, "lon": 25.0},
    "BG": {"lat": 42.7, "lon": 25.5},
    "HR": {"lat": 45.1, "lon": 15.2},
    "SK": {"lat": 48.7, "lon": 19.7},
    "SI": {"lat": 46.2, "lon": 14.8},
    "EE": {"lat": 58.6, "lon": 25.0},
    "LV": {"lat": 56.9, "lon": 24.6},
    "LT": {"lat": 55.2, "lon": 23.9},
}


def ingest_electricity_data(zones: list[str] = None) -> dict:
    """Core ingestion logic - fetches from Electricity Maps API."""
    
    em_api_key = os.environ["ELECTRICITY_MAPS_API_KEY"]
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]
    
    api_base_url = os.environ.get(
        "ELECTRICITY_MAPS_API_URL", 
        "https://api.electricitymap.org/v3"
    ).rstrip("/")
    
    if zones is None:
        zones = os.environ.get("ZONES", "NL,DE,FR,GB,BE,ES,IT,PT,AT,CH,PL,DK,SE,NO,FI").split(",")
    
    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    indexed_count = 0
    errors = []
    results = []

    for zone in zones:
        zone = zone.strip().upper()
        try:
            resp = requests.get(
                f"{api_base_url}/power-breakdown/latest",
                params={"zone": zone},
                headers={"auth-token": em_api_key},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            # Get coordinates for this zone
            coords = ZONE_COORDINATES.get(zone[:2], {})

            # Calculate totals from breakdowns
            consumption_breakdown = data.get("powerConsumptionBreakdown") or {}
            production_breakdown = data.get("powerProductionBreakdown") or {}
            
            consumption_total = sum(v for v in consumption_breakdown.values() if v is not None)
            production_total = sum(v for v in production_breakdown.values() if v is not None)

            doc = {
                "@timestamp": data.get("datetime", datetime.utcnow().isoformat()),
                "datetime": data.get("datetime"),
                "zone": data.get("zone"),
                "country_code": data.get("zone", "")[:2],
                "carbon_intensity": data.get("carbonIntensity"),
                "fossil_free_percentage": data.get("fossilFreePercentage"),
                "renewable_percentage": data.get("renewablePercentage"),
                "is_estimated": data.get("isEstimated"),
                "estimation_method": data.get("estimationMethod"),
                "power_consumption_breakdown": consumption_breakdown,
                "power_production_breakdown": production_breakdown,
                "power_consumption_total": consumption_total,
                "power_production_total": production_total,
                "location": coords if coords else None,
                "data_source": "electricity_maps_api",
                "updated_at": datetime.utcnow().isoformat()
            }

            es.index(index="electricity-maps", document=doc)
            indexed_count += 1
            results.append({
                "zone": zone, 
                "status": "ok", 
                "carbon_intensity": doc["carbon_intensity"],
                "renewable_percentage": doc["renewable_percentage"]
            })
            logging.info(f"Indexed data for zone: {zone}")

        except requests.RequestException as e:
            errors.append(f"{zone}: HTTP error - {str(e)}")
            results.append({"zone": zone, "status": "error", "message": str(e)})
            logging.error(f"Failed to fetch data for {zone}: {e}")
        except Exception as e:
            errors.append(f"{zone}: {str(e)}")
            results.append({"zone": zone, "status": "error", "message": str(e)})
            logging.error(f"Failed to process {zone}: {e}")

    return {
        "indexed": indexed_count,
        "total": len(zones),
        "errors": errors,
        "results": results
    }


# Timer trigger - runs every hour
@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def electricity_maps_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.info("Timer is past due!")
    
    result = ingest_electricity_data()
    logging.info(f"Timer completed: {result['indexed']}/{result['total']} zones indexed")


# HTTP trigger - manual execution
@app.route(route="ingest", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def electricity_maps_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Manual ingest triggered via HTTP")
    
    # Allow overriding zones via query param or body
    zones = None
    zones_param = req.params.get("zones")
    
    if zones_param:
        zones = zones_param.split(",")
    elif req.method == "POST":
        try:
            body = req.get_json()
            zones = body.get("zones")
        except ValueError:
            pass
    
    result = ingest_electricity_data(zones)
    
    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if not result["errors"] else 207,
        mimetype="application/json"
    )