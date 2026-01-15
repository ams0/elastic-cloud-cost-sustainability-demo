import azure.functions as func
import logging
import requests
from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime

app = func.FunctionApp()


def ingest_carbon_intensity_data(regions: list[str] = None) -> dict:
    """Core ingestion logic - fetches from UK Carbon Intensity API (no auth required)."""
    
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]
    
    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    # UK DNO Region coordinates for map visualization
    REGION_COORDINATES = {
        1: {"lat": 57.5, "lon": -5.0},      # North Scotland
        2: {"lat": 55.9, "lon": -3.2},      # South Scotland
        3: {"lat": 53.8, "lon": -2.6},      # North West England
        4: {"lat": 54.9, "lon": -1.6},      # North East England
        5: {"lat": 53.8, "lon": -1.5},      # Yorkshire
        6: {"lat": 53.2, "lon": -3.0},      # North Wales & Merseyside
        7: {"lat": 51.6, "lon": -3.4},      # South Wales
        8: {"lat": 52.5, "lon": -2.0},      # West Midlands
        9: {"lat": 52.9, "lon": -0.5},      # East Midlands
        10: {"lat": 52.2, "lon": 0.9},      # East England
        11: {"lat": 50.7, "lon": -3.5},     # South West England
        12: {"lat": 51.0, "lon": -1.3},     # South England
        13: {"lat": 51.5, "lon": -0.1},     # London
        14: {"lat": 51.3, "lon": 0.5},      # South East England
        15: {"lat": 52.5, "lon": -1.5},     # England (aggregate)
        16: {"lat": 56.5, "lon": -4.0},     # Scotland (aggregate)
        17: {"lat": 52.0, "lon": -3.5},     # Wales (aggregate)
    }

    indexed_count = 0
    errors = []
    results = []

    try:
        # Fetch all regional data in one call
        resp = requests.get(
            "https://api.carbonintensity.org.uk/regional",
            headers={"Accept": "application/json"},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        for region_data in data.get("data", []):
            from_time = region_data.get("from")
            to_time = region_data.get("to")
            
            for region in region_data.get("regions", []):
                region_id = region.get("regionid")
                shortname = region.get("shortname")
                
                # Filter by regions if specified
                if regions and str(region_id) not in regions and shortname not in regions:
                    continue
                
                try:
                    intensity = region.get("intensity", {})
                    generation_mix = region.get("generationmix", [])
                    
                    # Build generation breakdown
                    generation_breakdown = {}
                    renewable_total = 0
                    fossil_total = 0
                    low_carbon_total = 0
                    
                    renewable_sources = ["wind", "solar", "hydro"]
                    fossil_sources = ["gas", "coal", "oil"]
                    low_carbon_sources = ["wind", "solar", "hydro", "nuclear", "biomass"]
                    
                    for gen in generation_mix:
                        fuel = gen.get("fuel", "").lower().replace(" ", "_")
                        perc = gen.get("perc", 0) or 0
                        generation_breakdown[fuel] = perc
                        
                        if fuel in renewable_sources:
                            renewable_total += perc
                        if fuel in fossil_sources:
                            fossil_total += perc
                        if fuel in low_carbon_sources:
                            low_carbon_total += perc

                    # Get coordinates for this region
                    coords = REGION_COORDINATES.get(region_id, {})

                    doc = {
                        "@timestamp": from_time or datetime.utcnow().isoformat(),
                        "datetime_from": from_time,
                        "datetime_to": to_time,
                        "region_id": region_id,
                        "region_name": shortname,
                        "dno_region": region.get("dnoregion"),
                        "country": "GB",
                        "carbon_intensity": intensity.get("forecast"),
                        "carbon_intensity_index": intensity.get("index"),
                        "generation_mix": generation_breakdown,
                        "renewable_percentage": round(renewable_total, 1),
                        "fossil_percentage": round(fossil_total, 1),
                        "low_carbon_percentage": round(low_carbon_total, 1),
                        "location": coords if coords else None,
                        "data_source": "carbonintensity.org.uk",
                        "updated_at": datetime.utcnow().isoformat()
                    }

                    es.index(index="electricity-maps", document=doc)
                    indexed_count += 1
                    results.append({
                        "region": shortname,
                        "status": "ok",
                        "carbon_intensity": intensity.get("forecast"),
                        "index": intensity.get("index")
                    })
                    logging.info(f"Indexed data for region: {shortname}")

                except Exception as e:
                    errors.append(f"{shortname}: {str(e)}")
                    results.append({"region": shortname, "status": "error", "message": str(e)})
                    logging.error(f"Failed to process {shortname}: {e}")

    except requests.RequestException as e:
        errors.append(f"API error: {str(e)}")
        logging.error(f"Failed to fetch data: {e}")

    return {
        "indexed": indexed_count,
        "total": len(results),
        "errors": errors,
        "results": results
    }


def ingest_national_data() -> dict:
    """Fetch national-level carbon intensity data."""
    
    es_cloud_id = os.environ["ELASTICSEARCH_CLOUD_ID"]
    es_api_key = os.environ["ELASTICSEARCH_API_KEY"]
    
    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)

    try:
        resp = requests.get(
            "https://api.carbonintensity.org.uk/intensity",
            headers={"Accept": "application/json"},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        
        intensity_data = data.get("data", [{}])[0]
        
        doc = {
            "@timestamp": intensity_data.get("from", datetime.utcnow().isoformat()),
            "datetime_from": intensity_data.get("from"),
            "datetime_to": intensity_data.get("to"),
            "region_id": 0,
            "region_name": "National",
            "dno_region": "National Grid",
            "country": "GB",
            "carbon_intensity": intensity_data.get("intensity", {}).get("actual") or intensity_data.get("intensity", {}).get("forecast"),
            "carbon_intensity_forecast": intensity_data.get("intensity", {}).get("forecast"),
            "carbon_intensity_index": intensity_data.get("intensity", {}).get("index"),
            "data_source": "carbonintensity.org.uk",
            "updated_at": datetime.utcnow().isoformat()
        }

        es.index(index="electricity-maps", document=doc)
        logging.info("Indexed national data")
        
        return {
            "status": "ok",
            "carbon_intensity": doc["carbon_intensity"],
            "index": doc["carbon_intensity_index"]
        }

    except Exception as e:
        logging.error(f"Failed to fetch national data: {e}")
        return {"status": "error", "message": str(e)}


# Timer trigger - runs every 30 minutes (API updates every 30 min)
@app.timer_trigger(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=False)
def carbon_intensity_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.info("Timer is past due!")
    
    # Ingest national data
    national_result = ingest_national_data()
    logging.info(f"National: {national_result}")
    
    # Ingest all regional data
    result = ingest_carbon_intensity_data()
    logging.info(f"Regional: {result['indexed']}/{result['total']} regions indexed")


# HTTP trigger - manual execution
@app.route(route="ingest", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def carbon_intensity_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Manual ingest triggered via HTTP")
    
    # Allow filtering by regions via query param or body
    regions = None
    regions_param = req.params.get("regions")
    
    if regions_param:
        regions = regions_param.split(",")
    elif req.method == "POST":
        try:
            body = req.get_json()
            regions = body.get("regions")
        except ValueError:
            pass
    
    # Ingest national data
    national_result = ingest_national_data()
    
    # Ingest regional data
    result = ingest_carbon_intensity_data(regions)
    result["national"] = national_result
    
    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if not result["errors"] else 207,
        mimetype="application/json"
    )