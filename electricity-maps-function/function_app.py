import azure.functions as func
import logging
import requests
from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

app = func.FunctionApp()

# Electricity Maps API Configuration
ELECTRICITY_MAPS_API_BASE = "https://api.electricitymap.org/v3"

# Common zones to monitor (can be expanded)
DEFAULT_ZONES = [
    "GB",  # Great Britain
    "DE",  # Germany
    "FR",  # France
    "US-CAL-CISO",  # California
    "US-NE-ISNE",  # New England
    "US-TEX-ERCO",  # Texas
    "ES",  # Spain
    "IT-NO",  # Italy North
    "NL",  # Netherlands
    "SE",  # Sweden
]


def get_carbon_intensity_latest(zone: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Fetch latest carbon intensity data for a zone."""
    try:
        url = f"{ELECTRICITY_MAPS_API_BASE}/carbon-intensity/latest"
        headers = {"auth-token": api_key}
        params = {"zone": zone}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch carbon intensity for {zone}: {e}")
        return None


def get_power_breakdown_latest(zone: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Fetch latest power breakdown data for a zone."""
    try:
        url = f"{ELECTRICITY_MAPS_API_BASE}/power-breakdown/latest"
        headers = {"auth-token": api_key}
        params = {"zone": zone}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch power breakdown for {zone}: {e}")
        return None


def get_carbon_intensity_history(zone: str, api_key: str, hours_back: int = 24) -> Optional[List[Dict[str, Any]]]:
    """Fetch historical carbon intensity data for a zone."""
    try:
        url = f"{ELECTRICITY_MAPS_API_BASE}/carbon-intensity/history"
        headers = {"auth-token": api_key}

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        params = {
            "zone": zone,
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z"
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get("history", [])
    except requests.RequestException as e:
        logging.error(f"Failed to fetch carbon intensity history for {zone}: {e}")
        return None


def calculate_renewable_percentage(power_breakdown: Dict[str, Any]) -> float:
    """Calculate renewable energy percentage from power breakdown."""
    renewable_sources = ["solar", "wind", "hydro", "geothermal", "biomass"]

    power_production = power_breakdown.get("powerProductionBreakdown", {})
    if not power_production:
        return 0.0

    total_renewable = sum(
        power_production.get(source, 0) or 0
        for source in renewable_sources
    )

    total_production = sum(
        value or 0
        for value in power_production.values()
    )

    if total_production == 0:
        return 0.0

    return round((total_renewable / total_production) * 100, 2)


def calculate_fossil_percentage(power_breakdown: Dict[str, Any]) -> float:
    """Calculate fossil fuel percentage from power breakdown."""
    fossil_sources = ["coal", "gas", "oil"]

    power_production = power_breakdown.get("powerProductionBreakdown", {})
    if not power_production:
        return 0.0

    total_fossil = sum(
        power_production.get(source, 0) or 0
        for source in fossil_sources
    )

    total_production = sum(
        value or 0
        for value in power_production.values()
    )

    if total_production == 0:
        return 0.0

    return round((total_fossil / total_production) * 100, 2)


def ingest_zone_data(zones: List[str], api_key: str, es: Elasticsearch) -> Dict[str, Any]:
    """Ingest latest data for specified zones."""
    results = []
    indexed_count = 0
    errors = []

    for zone in zones:
        try:
            # Fetch carbon intensity
            carbon_data = get_carbon_intensity_latest(zone, api_key)
            if not carbon_data:
                errors.append(f"{zone}: Failed to fetch carbon intensity")
                continue

            # Fetch power breakdown
            power_data = get_power_breakdown_latest(zone, api_key)

            # Build document
            doc = {
                "@timestamp": carbon_data.get("datetime", datetime.utcnow().isoformat()),
                "zone": zone,
                "carbon_intensity": carbon_data.get("carbonIntensity"),
                "fossil_free_percentage": carbon_data.get("fossilFreePercentage"),
                "renewable_percentage": carbon_data.get("renewablePercentage"),
                "data_source": "electricitymap.org",
                "updated_at": datetime.utcnow().isoformat()
            }

            # Add power breakdown if available
            if power_data:
                doc["power_production_breakdown"] = power_data.get("powerProductionBreakdown", {})
                doc["power_consumption_breakdown"] = power_data.get("powerConsumptionBreakdown", {})
                doc["power_import_breakdown"] = power_data.get("powerImportBreakdown", {})
                doc["power_export_breakdown"] = power_data.get("powerExportBreakdown", {})

                # Calculate additional metrics
                doc["calculated_renewable_percentage"] = calculate_renewable_percentage(power_data)
                doc["calculated_fossil_percentage"] = calculate_fossil_percentage(power_data)

            # Index to Elasticsearch
            es.index(index="electricity-maps", document=doc)
            indexed_count += 1

            results.append({
                "zone": zone,
                "status": "ok",
                "carbon_intensity": doc.get("carbon_intensity"),
                "renewable_percentage": doc.get("renewable_percentage")
            })

            logging.info(f"Indexed data for zone: {zone}")

        except Exception as e:
            errors.append(f"{zone}: {str(e)}")
            results.append({
                "zone": zone,
                "status": "error",
                "message": str(e)
            })
            logging.error(f"Failed to process {zone}: {e}")

    return {
        "indexed": indexed_count,
        "total": len(zones),
        "errors": errors,
        "results": results
    }


def ingest_historical_data(zone: str, api_key: str, es: Elasticsearch, hours_back: int = 24) -> Dict[str, Any]:
    """Ingest historical data for a zone."""
    try:
        history = get_carbon_intensity_history(zone, api_key, hours_back)

        if not history:
            return {
                "zone": zone,
                "status": "error",
                "message": "No historical data available"
            }

        indexed_count = 0
        for record in history:
            doc = {
                "@timestamp": record.get("datetime", datetime.utcnow().isoformat()),
                "zone": zone,
                "carbon_intensity": record.get("carbonIntensity"),
                "fossil_free_percentage": record.get("fossilFreePercentage"),
                "renewable_percentage": record.get("renewablePercentage"),
                "data_source": "electricitymap.org",
                "data_type": "historical",
                "updated_at": datetime.utcnow().isoformat()
            }

            es.index(index="electricity-maps", document=doc)
            indexed_count += 1

        logging.info(f"Indexed {indexed_count} historical records for {zone}")

        return {
            "zone": zone,
            "status": "ok",
            "indexed": indexed_count
        }

    except Exception as e:
        logging.error(f"Failed to ingest historical data for {zone}: {e}")
        return {
            "zone": zone,
            "status": "error",
            "message": str(e)
        }


# Timer trigger - runs every hour
@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def electricity_maps_timer(timer: func.TimerRequest) -> None:
    """Timer-triggered function to periodically ingest Electricity Maps data."""
    if timer.past_due:
        logging.info("Timer is past due!")

    api_key = os.environ["ELECTRICITY_MAPS_API_KEY"]
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]

    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    # Ingest data for default zones
    result = ingest_zone_data(DEFAULT_ZONES, api_key, es)
    logging.info(f"Timer trigger: {result['indexed']}/{result['total']} zones indexed")


# HTTP trigger - manual execution
@app.route(route="ingest", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def electricity_maps_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP-triggered function for manual data ingestion."""
    logging.info("Manual ingest triggered via HTTP")

    api_key = os.environ["ELECTRICITY_MAPS_API_KEY"]
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]

    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    # Parse zones from query params or body
    zones = DEFAULT_ZONES
    zones_param = req.params.get("zones")

    if zones_param:
        zones = zones_param.split(",")
    elif req.method == "POST":
        try:
            body = req.get_json()
            zones = body.get("zones", DEFAULT_ZONES)
        except ValueError:
            pass

    # Ingest data
    result = ingest_zone_data(zones, api_key, es)

    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if not result["errors"] else 207,
        mimetype="application/json"
    )


# HTTP trigger - historical data ingestion
@app.route(route="ingest-history", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def electricity_maps_history_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP-triggered function for historical data ingestion."""
    logging.info("Historical ingest triggered via HTTP")

    api_key = os.environ["ELECTRICITY_MAPS_API_KEY"]
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]

    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    # Parse parameters
    zone = req.params.get("zone", "GB")
    hours_back = int(req.params.get("hours", "24"))

    if req.method == "POST":
        try:
            body = req.get_json()
            zone = body.get("zone", zone)
            hours_back = body.get("hours", hours_back)
        except ValueError:
            pass

    # Ingest historical data
    result = ingest_historical_data(zone, api_key, es, hours_back)

    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if result["status"] == "ok" else 500,
        mimetype="application/json"
    )
