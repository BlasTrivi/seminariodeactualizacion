"""Items del scraper: estructura de los datos que se extraen de Cúspide."""
from __future__ import annotations

import scrapy


class LibroCuspideItem(scrapy.Item):
    """Un resultado de la búsqueda de uno de nuestros libros en Cúspide."""

    # Datos de la búsqueda
    libro_id = scrapy.Field()          # id del libro en nuestro catálogo
    busqueda = scrapy.Field()          # texto buscado (título)
    posicion = scrapy.Field()          # lugar en los resultados (1 a 10)
    fecha_extraccion = scrapy.Field()  # momento de la ejecución
    # Datos del producto publicado por el competidor
    titulo = scrapy.Field()
    autor = scrapy.Field()
    isbn = scrapy.Field()
    url = scrapy.Field()
    precio = scrapy.Field()                     # precio en pesos
    precio_usd = scrapy.Field()                 # precio informado en U$s
    url_imagen = scrapy.Field()
    formas_pago = scrapy.Field()                # medios de pago nacionales
    formas_pago_internacional = scrapy.Field()  # medios de pago del exterior
    descripcion = scrapy.Field()
    # Calculado por los pipelines
    coincidencia = scrapy.Field()
