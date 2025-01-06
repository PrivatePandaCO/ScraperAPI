# scraper_server_X/scraper_manager.py
import importlib
import os
import sys
from typing import Dict
from common.logging import setup_logging

logger = setup_logging("scraper_manager")

class ScraperManager:
    def __init__(self, scraper_directory: str):
        self.scraper_directory = scraper_directory
        self.scrapers: Dict[str, any] = {}
        sys.path.append(scraper_directory)
        self.load_scrapers()

    def load_scrapers(self):
        logger.info("Loading scrapers...")
        for filename in os.listdir(self.scraper_directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                self.load_scraper(module_name)
        logger.info("Scrapers loaded successfully.")

    def load_scraper(self, module_name: str):
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            module = sys.modules[module_name]
            self.scrapers[module_name] = module
            logger.info(f"Loaded scraper: {module_name}")
        except Exception as e:
            logger.error(f"Error loading scraper {module_name}: {e}")

    def get_scraper(self, name: str):
        self.load_scrapers()  # Reload scrapers on each request
        return self.scrapers.get(name)
