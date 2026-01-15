import azure.functions as func
import logging
import requests
from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

app = func.FunctionApp()

# European countries with their ENTSO-E area codes and coordinates
EUROPEAN_COUNTRIES = {
    "AT": {"name": "Austria", "code": "10YAT-APG------L", "lat": 47.5162, "lon": 14.5501},
    "BE": {"name": "Belgium", "code": "10YBE----------2", "lat": 50.5039, "lon": 4.4699},
    "BG": {"name": "Bulgaria", "code": "10YCA-BULGARIA-R", "lat": 42.7339, "lon": 25.4858},
    "HR": {"name": "Croatia", "code": "10YHR-HEP------M", "lat": 45.1, "lon": 15.2},
    "CZ": {"name": "Czech Republic", "code": "10YCZ-CEPS-----N", "lat": 49.8175, "lon": 15.4730},
    "DK": {"name": "Denmark", "code": "10Y1001A1001A65H", "lat": 56.2639, "lon": 9.5018},
    "EE": {"name": "Estonia", "code": "10Y1001A1001A39I", "lat": 58.5953, "lon": 25.0136},
    "FI": {"name": "Finland", "code": "10YFI-1--------U", "lat": 61.9241, "lon": 25.7482},
    "FR": {"name": "France", "code": "10YFR-RTE------C", "lat": 46.2276, "lon": 2.2137},
    "DE": {"name": "Germany", "code": "10Y1001A1001A83F", "lat": 51.1657, "lon": 10.4515},
    "GR": {"name": "Greece", "code": "10YGR-HTSO-----Y", "lat": 39.0742, "lon": 21.8243},
    "HU": {"name": "Hungary", "code": "10YHU-MAVIR----U", "lat": 47.1625, "lon": 19.5033},
    "IE": {"name": "Ireland", "code": "10YIE-1001A00010", "lat": 53.4129, "lon": -8.2439},
    "IT": {"name": "Italy", "code": "10YIT-GRTN-----B", "lat": 41.8719, "lon": 12.5674},
    "LV": {"name": "Latvia", "code": "10YLV-1001A00074", "lat": 56.8796, "lon": 24.6032},
    "LT": {"name": "Lithuania", "code": "10YLT-1001A0008Q", "lat": 55.1694, "lon": 23.8813},
    "LU": {"name": "Luxembourg", "code": "10YLU-CEGEDEL-NQ", "lat": 49.8153, "lon": 6.1296},
    "NL": {"name": "Netherlands", "code": "10YNL----------L", "lat": 52.1326, "lon": 5.2913},
    "NO": {"name": "Norway", "code": "10YNO-0--------C", "lat": 60.4720, "lon": 8.4689},
    "PL": {"name": "Poland", "code": "10YPL-AREA-----S", "lat": 51.9194, "lon": 19.1451},
    "PT": {"name": "Portugal", "code": "10YPT-REN------W", "lat": 39.3999, "lon": -8.2245},
    "RO": {"name": "Romania", "code": "10YRO-TEL------P", "lat": 45.9432, "lon": 24.9668},
    "SK": {"name": "Slovakia", "code": "10YSK-SEPS-----K", "lat": 48.6690, "lon": 19.6990},
    "SI": {"name": "Slovenia", "code": "10YSI-ELES-----O", "lat": 46.1512, "lon": 14.9955},
    "ES": {"name": "Spain", "code": "10YES-REE------0", "lat": 40.4637, "lon": -3.7492},
    "SE": {"name": "Sweden", "code": "10YSE-1--------K", "lat": 60.1282, "lon": 18.6435},
    "CH": {"name": "Switzerland", "code": "10YCH-SWISSGRIDZ", "lat": 46.8182, "lon": 8.2275},
    "GB": {"name": "United Kingdom", "code": "10YGB----------A", "lat": 55.3781, "lon": -3.4360},
}


def parse_entsoe_xml(xml_content: str) -> List[Dict]:
    """Parse ENTSO-E XML response and extract time series data."""
    try:
        root = ET.fromstring(xml_content)
        namespace = {'ns': 'urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0'}
        
        time_series_list = root.findall('.//ns:TimeSeries', namespace)
        results = []
        
        for ts in time_series_list:
            # Get production type if available
            prod_type_elem = ts.find('.//ns:MktPSRType/ns:psrType', namespace)
            prod_type = prod_type_elem.text if prod_type_elem is not None else None
            
            # Parse time interval
            period = ts.find('.//ns:Period', namespace)
            if period is None:
                continue
                
            time_interval = period.find('.//ns:timeInterval', namespace)
            start_time = time_interval.find('ns:start', namespace).text if time_interval is not None else None
            end_time = time_interval.find('ns:end', namespace).text if time_interval is not None else None
            
            # Parse points
            points = period.findall('.//ns:Point', namespace)
            for point in points:
                position = point.find('ns:position', namespace)
                quantity = point.find('ns:quantity', namespace)
                
                if position is not None and quantity is not None:
                    results.append({
                        'production_type': prod_type,
                        'start_time': start_time,
                        'end_time': end_time,
                        'position': int(position.text),
                        'quantity': float(quantity.text)
                    })
        
        return results
    except Exception as e:
        logging.error(f"Error parsing XML: {e}")
        return []


def fetch_entsoe_data(api_key: str, document_type: str, area_code: str, 
                      start: datetime, end: datetime) -> Optional[str]:
    """Fetch data from ENTSO-E API."""
    base_url = "https://web-api.tp.entsoe.eu/api"
    
    params = {
        'securityToken': api_key,
        'documentType': document_type,
        'in_Domain': area_code,
        'periodStart': start.strftime('%Y%m%d%H%M'),
        'periodEnd': end.strftime('%Y%m%d%H%M')
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None


def get_generation_mix(api_key: str, area_code: str, start: datetime, end: datetime) -> Dict:
    """Get generation mix data for a country."""
    # A75 = Actual Generation per Type
    xml_data = fetch_entsoe_data(api_key, 'A75', area_code, start, end)
    
    if not xml_data:
        return {}
    
    parsed_data = parse_entsoe_xml(xml_data)
    
    # Aggregate by production type
    generation_mix = {}
    total_generation = 0
    
    # ENTSO-E production type codes
    prod_type_mapping = {
        'B01': 'biomass',
        'B02': 'fossil_brown_coal',
        'B03': 'fossil_coal',
        'B04': 'fossil_gas',
        'B05': 'fossil_hard_coal',
        'B06': 'fossil_oil',
        'B09': 'geothermal',
        'B10': 'hydro_pumped_storage',
        'B11': 'hydro_run_of_river',
        'B12': 'hydro_water_reservoir',
        'B13': 'marine',
        'B14': 'nuclear',
        'B15': 'other_renewable',
        'B16': 'solar',
        'B17': 'waste',
        'B18': 'wind_offshore',
        'B19': 'wind_onshore',
        'B20': 'other',
    }
    
    for item in parsed_data:
        prod_type = item.get('production_type')
        quantity = item.get('quantity', 0)
        
        if prod_type and quantity > 0:
            fuel_name = prod_type_mapping.get(prod_type, f'unknown_{prod_type}')
            generation_mix[fuel_name] = generation_mix.get(fuel_name, 0) + quantity
            total_generation += quantity
    
    # Convert to percentages
    if total_generation > 0:
        generation_mix = {k: round((v / total_generation) * 100, 2) 
                         for k, v in generation_mix.items()}
    
    return generation_mix


def get_load_data(api_key: str, area_code: str, start: datetime, end: datetime) -> Optional[float]:
    """Get actual total load for a country."""
    # A65 = Actual Total Load
    xml_data = fetch_entsoe_data(api_key, 'A65', area_code, start, end)
    
    if not xml_data:
        return None
    
    parsed_data = parse_entsoe_xml(xml_data)
    
    if parsed_data:
        # Return the most recent load value
        return parsed_data[-1].get('quantity')
    
    return None


def calculate_carbon_intensity(generation_mix: Dict) -> float:
    """Calculate approximate carbon intensity from generation mix."""
    # Carbon intensity factors (gCO2/kWh)
    carbon_factors = {
        'biomass': 230,
        'fossil_brown_coal': 900,
        'fossil_coal': 820,
        'fossil_gas': 490,
        'fossil_hard_coal': 820,
        'fossil_oil': 650,
        'geothermal': 38,
        'hydro_pumped_storage': 24,
        'hydro_run_of_river': 24,
        'hydro_water_reservoir': 24,
        'marine': 24,
        'nuclear': 12,
        'other_renewable': 50,
        'solar': 45,
        'waste': 350,
        'wind_offshore': 12,
        'wind_onshore': 11,
        'other': 400,
    }
    
    total_intensity = 0
    for fuel, percentage in generation_mix.items():
        factor = carbon_factors.get(fuel, 500)
        total_intensity += (percentage / 100) * factor
    
    return round(total_intensity, 2)


def calculate_renewable_percentage(generation_mix: Dict) -> float:
    """Calculate percentage of renewable energy."""
    renewable_sources = [
        'hydro_run_of_river', 'hydro_water_reservoir', 'wind_offshore', 
        'wind_onshore', 'solar', 'geothermal', 'marine', 'other_renewable'
    ]
    
    renewable_total = sum(generation_mix.get(source, 0) for source in renewable_sources)
    return round(renewable_total, 2)


def ingest_entsoe_data(countries: Optional[List[str]] = None) -> Dict:
    """Core ingestion logic - fetches data from ENTSO-E API."""
    
    es_cloud_id = os.environ.get("ELASTICSEARCH_CLOUD_ID")
    es_api_key = os.environ.get("ELASTICSEARCH_API_KEY")
    entsoe_api_key = os.environ.get("ENTSOE_API_KEY")
    
    if not entsoe_api_key:
        return {"error": "ENTSOE_API_KEY not configured"}
    
    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)
    
    indexed_count = 0
    errors = []
    results = []
    
    # Time range: last hour
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    
    # Filter countries if specified
    countries_to_process = EUROPEAN_COUNTRIES
    if countries:
        countries_to_process = {k: v for k, v in EUROPEAN_COUNTRIES.items() 
                               if k in countries or v['name'] in countries}
    
    for country_code, country_info in countries_to_process.items():
        try:
            logging.info(f"Processing {country_info['name']} ({country_code})")
            
            # Get generation mix
            generation_mix = get_generation_mix(
                entsoe_api_key, 
                country_info['code'], 
                start, 
                end
            )
            
            # Get load data
            load = get_load_data(
                entsoe_api_key,
                country_info['code'],
                start,
                end
            )
            
            # Calculate metrics
            carbon_intensity = calculate_carbon_intensity(generation_mix) if generation_mix else None
            renewable_pct = calculate_renewable_percentage(generation_mix) if generation_mix else None
            
            # Calculate fossil percentage
            fossil_sources = ['fossil_brown_coal', 'fossil_coal', 'fossil_gas', 
                            'fossil_hard_coal', 'fossil_oil']
            fossil_pct = sum(generation_mix.get(source, 0) for source in fossil_sources) if generation_mix else None
            
            # Calculate low carbon (renewable + nuclear)
            low_carbon_pct = renewable_pct + generation_mix.get('nuclear', 0) if renewable_pct and generation_mix else None
            
            doc = {
                "@timestamp": datetime.utcnow().isoformat(),
                "datetime_from": start.isoformat(),
                "datetime_to": end.isoformat(),
                "country_code": country_code,
                "country_name": country_info['name'],
                "area_code": country_info['code'],
                "location": {
                    "lat": country_info['lat'],
                    "lon": country_info['lon']
                },
                "generation_mix": generation_mix,
                "total_load_mw": load,
                "carbon_intensity": carbon_intensity,
                "renewable_percentage": renewable_pct,
                "fossil_percentage": round(fossil_pct, 2) if fossil_pct else None,
                "low_carbon_percentage": round(low_carbon_pct, 2) if low_carbon_pct else None,
                "data_source": "entsoe.eu",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            es.index(index="entsoe-energy", document=doc)
            indexed_count += 1
            
            results.append({
                "country": country_info['name'],
                "status": "ok",
                "carbon_intensity": carbon_intensity,
                "renewable_pct": renewable_pct,
                "load_mw": load
            })
            
            logging.info(f"Indexed data for {country_info['name']}")
            
        except Exception as e:
            error_msg = f"{country_info['name']}: {str(e)}"
            errors.append(error_msg)
            results.append({
                "country": country_info['name'],
                "status": "error",
                "message": str(e)
            })
            logging.error(f"Failed to process {country_info['name']}: {e}")
    
    return {
        "indexed": indexed_count,
        "total": len(results),
        "errors": errors,
        "results": results
    }


# Timer trigger - runs every hour (ENTSO-E data updates frequently)
@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def entsoe_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.info("Timer is past due!")
    
    result = ingest_entsoe_data()
    logging.info(f"ENTSO-E ingestion: {result['indexed']}/{result['total']} countries indexed")
    
    if result['errors']:
        logging.warning(f"Errors: {result['errors']}")


# HTTP trigger - manual execution
@app.route(route="ingest", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def entsoe_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Manual ENTSO-E ingest triggered via HTTP")
    
    # Allow filtering by countries via query param or body
    countries = None
    countries_param = req.params.get("countries")
    
    if countries_param:
        countries = countries_param.split(",")
    elif req.method == "POST":
        try:
            body = req.get_json()
            countries = body.get("countries")
        except ValueError:
            pass
    
    result = ingest_entsoe_data(countries)
    
    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if not result.get("errors") else 207,
        mimetype="application/json"
    )
