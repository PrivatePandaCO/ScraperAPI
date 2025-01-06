# public_server/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import os
import asyncio
from load_balancer import LoadBalancer
from common.logging import setup_logging

# Setup logging
logger = setup_logging("public_server")

app = FastAPI()

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'public_server_config.json')
with open(CONFIG_PATH) as f:
    config = json.load(f)

LICENSE_SERVER_URL = f"http://{config['license_server']['ip']}:{config['license_server']['port']}/validate"
SCRAPER_SERVERS = config['scraper_servers']

load_balancer = LoadBalancer(scraper_servers=SCRAPER_SERVERS)

# Pydantic Models
class ClientRequest(BaseModel):
    license_key: str
    scraper_name: str
    params: dict

class ClientResponse(BaseModel):
    status: str
    data: dict

@app.post("/submit", response_model=ClientResponse)
async def submit_job(request: ClientRequest):
    # Validate license key
    try:
        validate_response = requests.post(
            LICENSE_SERVER_URL,
            json={"key": request.license_key},
            timeout=5
        )
        if validate_response.status_code != 200:
            logger.warning(f"License validation failed for key {request.license_key}")
            raise HTTPException(status_code=400, detail="Invalid license key")
        license_info = validate_response.json()
    except requests.RequestException:
        logger.error("License server is unreachable")
        raise HTTPException(status_code=500, detail="License server error")

    allowed_scrapers = license_info.get("scrapers", [])
    if "all" not in allowed_scrapers and request.scraper_name not in allowed_scrapers:
        logger.warning(f"Scraper {request.scraper_name} not allowed for license {request.license_key}")
        raise HTTPException(status_code=403, detail="Scraper not allowed for this license")

    # Select an appropriate scraper server
    server = await load_balancer.select_server(request.scraper_name)
    if not server:
        logger.error(f"No available servers for scraper {request.scraper_name}")
        raise HTTPException(status_code=503, detail="No scraper servers available for this scraper")

    # Assign job to selected server
    try:
        scrape_response = requests.post(
            f"http://{server['ip']}:{server['port']}/scrape",
            json={
                "scraper_name": request.scraper_name,
                "params": request.params
            },
            timeout=30
        )
        if scrape_response.status_code == 200:
            logger.info(f"Job assigned to {server['name']} successfully")
            return {"status": "success", "data": scrape_response.json()}
        else:
            logger.error(f"Scraper server {server['name']} returned error: {scrape_response.text}")
            raise HTTPException(status_code=500, detail="Scraper server error")
    except requests.RequestException:
        logger.error(f"Failed to communicate with scraper server {server['name']}")
        raise HTTPException(status_code=503, detail="Scraper server unreachable")

if __name__ == "__main__":
    import uvicorn
    public_server_config = config["public_server"]
    uvicorn.run(app, host=public_server_config["ip"], port=public_server_config["port"])
