"""Ejecución del ``CuspideSpider`` desde Python.

Scrapy corre sobre el *reactor* de Twisted, que solo puede iniciarse una
vez por proceso: si el spider se lanzara dentro del proceso del menú (o
del notebook) la segunda ejecución fallaría con ``ReactorNotRestartable``.
Por eso ``ServicioScraping`` ejecuta este módulo en un proceso aparte::

    python -m book_manager.scraper.runner --resumen reportes/x.json

El spider deja los resultados en la base de datos (``BaseDatosPipeline``),
los exporta también a JSON y escribe un resumen que lee el servicio.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from book_manager.scraper import settings as configuracion
from book_manager.scraper.spiders.cuspide import CuspideSpider


def ejecutar_spider(archivo_resumen: Path,
                    archivo_resultados: Optional[Path] = None,
                    libros: Optional[str] = None,
                    fecha_extraccion: Optional[str] = None) -> None:
    """Corre el spider (bloquea hasta que termina).

    Args:
        archivo_resumen (Path): JSON donde se deja el resumen de la corrida.
        archivo_resultados (Optional[Path]): JSON con todos los items.
        libros (Optional[str]): Ids de libros separados por coma.
        fecha_extraccion (Optional[str]): Fecha y hora de la ejecución.
    """
    ajustes = Settings()
    ajustes.setmodule(configuracion, priority="project")
    ajustes.set("RESUMEN_SCRAPING", str(archivo_resumen))
    if archivo_resultados is not None:
        ajustes.set("FEEDS", {str(archivo_resultados): {
            "format": "json", "encoding": "utf-8", "indent": 2,
            "overwrite": True}})
    proceso = CrawlerProcess(ajustes)
    proceso.crawl(CuspideSpider, libros=libros,
                  fecha_extraccion=fecha_extraccion)
    proceso.start()


def _argumentos(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper de Cúspide")
    parser.add_argument("--resumen", required=True, type=Path)
    parser.add_argument("--resultados", type=Path)
    parser.add_argument("--libros", default=None)
    parser.add_argument("--fecha", default=None)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _argumentos()
    ejecutar_spider(args.resumen, args.resultados, args.libros, args.fecha)
