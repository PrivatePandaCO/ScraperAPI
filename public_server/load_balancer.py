# public_server/load_balancer.py
import requests
import asyncio
from typing import List, Dict
from common.utils import get_cpu_usage, get_memory_usage
from common.logging import setup_logging

logger = setup_logging("load_balancer")

class LoadBalancer:
    def __init__(self, scraper_servers: List[Dict], threshold_cpu: float = 80.0, threshold_memory: float = 80.0):
        self.scraper_servers = scraper_servers
        self.threshold_cpu = threshold_cpu
        self.threshold_memory = threshold_memory

    async def get_server_load(self, server: Dict) -> float:
        try:
            response = requests.get(f"http://{server['ip']}:{server['port']}/load", timeout=5)
            if response.status_code == 200:
                load = response.json().get("load", 100.0)
                logger.info(f"Load for {server['name']}: {load}%")
                return load
        except requests.RequestException:
            logger.error(f"Failed to get load from {server['name']}")
        return 100.0  # Treat unreachable server as fully loaded

    async def select_server(self, scraper_name: str) -> Dict:
        eligible_servers = [
            server for server in self.scraper_servers
            if "all" in server.get("scrapers", []) or scraper_name in server.get("scrapers", [])
        ]
        if not eligible_servers:
            logger.warning(f"No eligible servers found for scraper {scraper_name}")
            return None

        # Gather loads concurrently
        loads = await asyncio.gather(*[self.get_server_load(s) for s in eligible_servers])
        server_loads = list(zip(eligible_servers, loads))
        # Sort by load ascending
        server_loads.sort(key=lambda x: x[1])

        for server, load in server_loads:
            if load < self.threshold_cpu and load < self.threshold_memory:
                logger.info(f"Selected server {server['name']} with load {load}%")
                return server
        logger.warning("No servers available below load thresholds")
        return None
