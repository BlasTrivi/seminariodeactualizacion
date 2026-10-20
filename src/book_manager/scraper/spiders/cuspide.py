"""CuspideSpider: busca nuestros libros en Cúspide y extrae sus datos.

Por cada libro del catálogo (y solo de nuestro catálogo) se busca por
título en el sitio y se procesan los 10 primeros resultados. De la ficha
de cada resultado se obtiene:

- precio (en pesos y en dólares si el sitio lo informa),
- URL de la imagen,
- formas de pago y su precio,
- descripción detallada (sinopsis),
- ISBN, título y autor (para saber si es el mismo libro).

Si una búsqueda no devuelve resultados se reintenta con el título
simplificado (sin signos de puntuación y sin subtítulo), porque el
buscador del sitio no encuentra, por ejemplo, "Sapiens: De animales a
dioses" pero sí "Sapiens De animales a dioses".
"""
from __future__ import annotations

import datetime
import re
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional
from urllib.parse import quote_plus, urlparse

import scrapy
from scrapy.crawler import Crawler
from scrapy.http import Response

from book_manager.database.connection import ConexionDB
from book_manager.entities.entities import Libro
from book_manager.repositories.repositories import Repositorios
from book_manager.scraper.items import LibroCuspideItem
from book_manager.scraper.loaders import LibroCuspideLoader

# Selectores del sitio (tema Flatsome de WooCommerce)
SEL_TARJETAS = "div.product-small.col"
SEL_TARJETA_URL = ".product-title a::attr(href), .name a::attr(href)"
SEL_TARJETA_TITULO = ".product-title a::text, .name a::text"
SEL_TARJETA_PRECIO = ".price ins bdi ::text, .price bdi ::text"
SEL_TARJETA_IMAGEN = ".box-image img::attr(src)"
SEL_FICHA = ".product-info h1"
SEL_TITULO = "h1.product_title::text"
SEL_AUTOR = ".product-info > span a::text"
XP_PRECIO_OFERTA = ('//div[contains(@class,"product-info")]'
                    '//p[contains(@class,"price")]//ins//bdi//text()')
XP_PRECIO = ('//div[contains(@class,"product-info")]'
             '//p[contains(@class,"price")]//bdi//text()')
XP_PRECIO_USD = ('//div[contains(@class,"product-info")]'
                 '//span[starts-with(normalize-space(text()), "U$s")]'
                 '/span/text()')
SEL_IMAGEN = (
    ".woocommerce-product-gallery__image img::attr(data-large_image)",
    ".woocommerce-product-gallery__image a::attr(href)",
    ".woocommerce-product-gallery__image img::attr(src)",
    "meta[property='og:image']::attr(content)",
)
SEL_ISBN = ".product_meta .sku::text"
SEL_SINOPSIS = ".livriz-text-synopsis ::text"
XP_DESCRIPCION = ('(//div[contains(@class,"product-footer")]'
                  '//div[contains(@class,"entry-content")])[1]'
                  '//p[not(contains(@class,"livriz-hidden"))]//text()')
SEL_DESCRIPCION_CORTA = (".woocommerce-product-details__short-description "
                         "::text")
SEL_PAGOS_ARGENTINA = "#contentPaymentsPopUpArg li::text"
SEL_PAGOS_EXTERIOR = "#contentPaymentsPopUpInt li::text"


def variantes_busqueda(titulo: str) -> List[str]:
    """Textos a buscar para un título, del más fiel al más simple."""
    variantes = [titulo.strip()]
    sin_signos = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", titulo)).strip()
    variantes.append(sin_signos)
    sin_subtitulo = re.split(r"[:.(\-–]", titulo)[0].strip()
    variantes.append(sin_subtitulo)
    resultado: List[str] = []
    for variante in variantes:
        if variante and variante.lower() not in (v.lower() for v in resultado):
            resultado.append(variante)
    return resultado


class CuspideSpider(scrapy.Spider):
    """Scraper de precios de Cúspide para los libros de nuestro catálogo."""

    name = "cuspide"
    allowed_domains = ["cuspide.com", "www.cuspide.com"]

    def __init__(self, libros: Optional[str] = None,
                 fecha_extraccion: Optional[str] = None,
                 *args: Any, **kwargs: Any) -> None:
        """
        Args:
            libros (Optional[str]): Ids de libros separados por coma; si no
                se indica se buscan todos los libros del catálogo.
            fecha_extraccion (Optional[str]): Fecha y hora con la que se
                registra la ejecución (por defecto, ahora).
        """
        super().__init__(*args, **kwargs)
        self.libros_ids: List[int] = [
            int(valor) for valor in str(libros or "").split(",")
            if valor.strip()]
        if fecha_extraccion:
            self.fecha_extraccion = datetime.datetime.fromisoformat(
                fecha_extraccion).replace(microsecond=0)
        else:
            self.fecha_extraccion = datetime.datetime.now().replace(
                microsecond=0)
        self.catalogo: Dict[int, Libro] = {}
        self.sin_resultados: List[int] = []

    @classmethod
    def from_crawler(cls, crawler: Crawler, *args: Any,
                     **kwargs: Any) -> "CuspideSpider":
        """Toma el dominio permitido de ``CUSPIDE_URL`` (configurable)."""
        spider = super().from_crawler(crawler, *args, **kwargs)
        host = urlparse(crawler.settings.get("CUSPIDE_URL")).hostname or ""
        spider.allowed_domains = [host.removeprefix("www.")]
        return spider

    # -- catálogo ------------------------------------------------------------

    def cargar_catalogo(self) -> Dict[int, Libro]:
        """Lee de la base de datos los libros a buscar (solo los nuestros)."""
        conexion = ConexionDB()
        try:
            repositorio = Repositorios.desde_conexion(conexion).libros
            libros = repositorio.leer_todos()
        finally:
            conexion.cerrar()
        if self.libros_ids:
            libros = [libro for libro in libros if libro.id in self.libros_ids]
        return {libro.id or 0: libro for libro in libros}

    def url_busqueda(self, texto: str) -> str:
        base = self.settings.get("CUSPIDE_URL").rstrip("/")
        return f"{base}/?s={quote_plus(texto)}&post_type=product"

    # -- pedidos ------------------------------------------------------------

    def _pedidos_iniciales(self) -> List[scrapy.Request]:
        """Una búsqueda por cada libro del catálogo."""
        self.catalogo = self.cargar_catalogo()
        if not self.catalogo:
            self.logger.error("No hay libros en la base para buscar.")
        self.logger.warning("Buscando %d libro(s) en %s", len(self.catalogo),
                            self.settings.get("CUSPIDE_URL"))
        return [self._pedido_busqueda(libro, intento=0)
                for libro in self.catalogo.values()]

    async def start(self) -> AsyncIterator[scrapy.Request]:
        """Pedidos iniciales (Scrapy 2.13 o superior)."""
        for pedido in self._pedidos_iniciales():
            yield pedido

    def start_requests(self) -> Iterator[scrapy.Request]:
        """Pedidos iniciales (Scrapy anterior a 2.13)."""
        yield from self._pedidos_iniciales()

    def _pedido_busqueda(self, libro: Libro, intento: int) -> scrapy.Request:
        texto = variantes_busqueda(libro.titulo)[intento]
        return scrapy.Request(
            self.url_busqueda(texto), callback=self.parse,
            cb_kwargs={"libro_id": libro.id, "busqueda": texto,
                       "intento": intento},
            dont_filter=True)

    def parse(self, response: Response, libro_id: int, busqueda: str,
              intento: int) -> Iterator[Any]:
        """Página de resultados: sigue los 10 primeros productos."""
        libro = self.catalogo[libro_id]
        if response.css(SEL_FICHA):
            # El sitio redirige a la ficha cuando hay un único resultado.
            yield from self.parse_producto(response, libro_id, busqueda, 1, {})
            return
        maximo = self.settings.getint("CUSPIDE_MAX_RESULTADOS", 10)
        tarjetas = response.css(SEL_TARJETAS)[:maximo]
        if not tarjetas:
            if intento + 1 < len(variantes_busqueda(libro.titulo)):
                yield self._pedido_busqueda(libro, intento + 1)
            else:
                self.sin_resultados.append(libro_id)
                self.logger.warning("Sin resultados para '%s'", libro.titulo)
            return
        for posicion, tarjeta in enumerate(tarjetas, start=1):
            url = tarjeta.css(SEL_TARJETA_URL).get()
            if not url:
                continue
            listado = {
                "titulo": tarjeta.css(SEL_TARJETA_TITULO).get(),
                "precio": tarjeta.css(SEL_TARJETA_PRECIO).getall(),
                "url_imagen": tarjeta.css(SEL_TARJETA_IMAGEN).get(),
            }
            yield response.follow(
                url, callback=self.parse_producto, dont_filter=True,
                cb_kwargs={"libro_id": libro_id, "busqueda": busqueda,
                           "posicion": posicion, "listado": listado})

    def parse_producto(self, response: Response, libro_id: int,
                       busqueda: str, posicion: int,
                       listado: Dict[str, Any]) -> Iterator[LibroCuspideItem]:
        """Ficha del producto: arma el item con el Item Loader."""
        loader = LibroCuspideLoader(response=response)
        loader.add_value("libro_id", libro_id)
        loader.add_value("busqueda", busqueda)
        loader.add_value("posicion", posicion)
        loader.add_value("fecha_extraccion",
                         self.fecha_extraccion.isoformat(sep=" "))
        loader.add_value("url", response.url)
        loader.add_css("titulo", SEL_TITULO)
        loader.add_value("titulo", listado.get("titulo"))
        loader.add_css("autor", SEL_AUTOR)
        loader.add_css("isbn", SEL_ISBN)
        loader.add_xpath("precio", XP_PRECIO_OFERTA)
        loader.add_xpath("precio", XP_PRECIO)
        loader.add_value("precio", listado.get("precio"))
        loader.add_xpath("precio_usd", XP_PRECIO_USD)
        for selector in SEL_IMAGEN:
            loader.add_css("url_imagen", selector)
        loader.add_value("url_imagen", listado.get("url_imagen"))
        if response.css(SEL_SINOPSIS):
            loader.add_css("descripcion", SEL_SINOPSIS)
        elif response.css(SEL_DESCRIPCION_CORTA):
            loader.add_css("descripcion", SEL_DESCRIPCION_CORTA)
        else:
            loader.add_xpath("descripcion", XP_DESCRIPCION)
        loader.add_css("formas_pago", SEL_PAGOS_ARGENTINA)
        loader.add_css("formas_pago_internacional", SEL_PAGOS_EXTERIOR)
        yield loader.load_item()
