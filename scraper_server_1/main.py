# scraper_server_X/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper_manager import ScraperManager
from common.utils import get_cpu_usage, get_memory_usage
import json
import os
import psutil
import uvicorn
from common.logging import setup_logging

# Setup logging
logger = setup_logging("scraper_server")

app = FastAPI()

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'scraper_server_1_config.json')  # Change for each server
with open(CONFIG_PATH) as f:
    config = json.load(f)

SCRAPER_DIRECTORY = os.path.join(os.path.dirname(__file__), 'scrapers')
scraper_manager = ScraperManager(scraper_directory=SCRAPER_DIRECTORY)

# Pydantic Models
class ScrapeRequest(BaseModel):
    scraper_name: str
    params: dict

class ScrapeResponse(BaseModel):
    status: str
    data: dict

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    scraper = scraper_manager.get_scraper(request.scraper_name)
    if not scraper:
        logger.warning(f"Scraper {request.scraper_name} not found")
        raise HTTPException(status_code=404, detail="Scraper not found")
    try:
        result = scraper.run(request.params)
        logger.info(f"Scraped data using {request.scraper_name}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error executing scraper {request.scraper_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load")
async def get_load():
    cpu = get_cpu_usage()
    memory = get_memory_usage()
    load = max(cpu, memory)  # Simplistic load metric
    logger.info(f"Current load - CPU: {cpu}%, Memory: {memory}%")
    return {"load": load}

if __name__ == "__main__":
    scraper_server_config = config["scraper_server"]
    uvicorn.run(app, host=scraper_server_config["ip"], port=scraper_server_config["port"])
