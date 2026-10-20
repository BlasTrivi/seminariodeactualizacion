"""Configuración de Scrapy para el scraper de Cúspide (Sprint 3).

Se respeta el ``robots.txt`` del sitio, se limita la concurrencia y se
agrega una demora entre pedidos para no sobrecargar al competidor.
"""
from __future__ import annotations

from typing import Dict

from book_manager.database.connection import variable_entorno

BOT_NAME = "book_manager_scraper"

SPIDER_MODULES = ["book_manager.scraper.spiders"]
NEWSPIDER_MODULE = "book_manager.scraper.spiders"

#: URL base del sitio (se lee del .env para poder cambiarla sin tocar código).
CUSPIDE_URL = variable_entorno("CUSPIDE_URL", "https://cuspide.com")

#: Cantidad de resultados de cada búsqueda que se procesan.
CUSPIDE_MAX_RESULTADOS = 10

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
              "BookManager-UGR/3.0")
ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 0.25
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5
COOKIES_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

#: Orden de los pipelines: limpieza -> formas de pago -> coincidencia -> DB.
ITEM_PIPELINES: Dict[str, int] = {
    "book_manager.scraper.pipelines.ValidacionPipeline": 100,
    "book_manager.scraper.pipelines.FormasPagoPipeline": 200,
    "book_manager.scraper.pipelines.CoincidenciaPipeline": 300,
    "book_manager.scraper.pipelines.BaseDatosPipeline": 400,
}

LOG_LEVEL = "WARNING"
FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
