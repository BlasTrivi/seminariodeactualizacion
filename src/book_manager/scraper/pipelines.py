"""Pipelines: procesan cada item que entrega el spider, en este orden.

1. ``ValidacionPipeline``: descarta los items incompletos (sin precio,
   título o URL) y los que superan la posición 10.
2. ``FormasPagoPipeline``: une cada forma de pago con su precio.
3. ``CoincidenciaPipeline``: calcula cuánto se parece el resultado a
   nuestro libro (ISBN, título y autor).
4. ``BaseDatosPipeline``: guarda los resultados en la tabla
   ``precios_web`` y, al terminar, marca el mejor resultado de cada libro.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from itemadapter import ItemAdapter
from scrapy import Spider
from scrapy.crawler import Crawler
from scrapy.exceptions import DropItem

from book_manager.database.connection import ConexionDB
from book_manager.entities.entities import Libro, PrecioWeb
from book_manager.repositories.repositories import (
    RepositorioPrecioWeb, Repositorios,
)

#: Puntaje mínimo para considerar que un resultado es nuestro libro.
COINCIDENCIA_MINIMA = 70
PALABRAS_VACIAS: Set[str] = {"el", "la", "los", "las", "de", "del", "y",
                             "a", "en", "un", "una", "the", "of", "and"}


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos (para comparar títulos)."""
    texto = str(texto or "").replace("¥", "ñ").lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", texto)).strip()


def palabras(texto: str) -> Set[str]:
    return {p for p in normalizar(texto).split() if p not in PALABRAS_VACIAS}


def puntaje_coincidencia(libro: Libro, titulo: str, autor: str = "",
                         isbn: str = "") -> int:
    """Puntaje de 0 a 100 que indica si el resultado es nuestro libro.

    - Mismo ISBN: 100 (es exactamente nuestra edición).
    - Mismo título: 85; el título web contiene el nuestro: 60; si no, la
      proporción de palabras de nuestro título presentes (hasta 50).
    - Coincidencia del autor: +10 (sin ISBN el máximo es 95).
    """
    if isbn and isbn == libro.isbn:
        return 100
    nuestro, web = normalizar(libro.titulo), normalizar(titulo)
    if not web:
        return 0
    if web == nuestro:
        puntaje = 85
    elif re.search(rf"(^|\s){re.escape(nuestro)}(\s|$)", web):
        puntaje = 60
    else:
        propias = palabras(libro.titulo)
        comunes = propias & palabras(titulo)
        puntaje = int(50 * len(comunes) / len(propias)) if propias else 0
    if autor and palabras(libro.autor) & palabras(autor):
        puntaje += 10
    return min(puntaje, 95)


class PipelineBase:
    """Guarda el crawler para acceder al spider y a la configuración.

    Desde Scrapy 2.13 los métodos de los pipelines dejan de recibir el
    argumento ``spider``; se lo obtiene del crawler, así el código
    funciona con versiones nuevas y anteriores de Scrapy.
    """

    def __init__(self, crawler: Optional[Crawler] = None) -> None:
        self._crawler = crawler

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "PipelineBase":
        return cls(crawler)

    def _spider(self, spider: Optional[Spider] = None) -> Any:
        if spider is not None:
            return spider
        assert self._crawler is not None
        return self._crawler.spider


class ValidacionPipeline(PipelineBase):
    """Descarta los resultados incompletos o fuera de los 10 primeros."""

    def process_item(self, item: Any, spider: Optional[Spider] = None) -> Any:
        spider = self._spider(spider)
        adaptador = ItemAdapter(item)
        for campo in ("libro_id", "titulo", "url", "precio"):
            if not adaptador.get(campo):
                raise DropItem(f"Resultado sin '{campo}': "
                               f"{adaptador.get('url')}")
        maximo = spider.settings.getint("CUSPIDE_MAX_RESULTADOS", 10)
        if int(adaptador["posicion"]) > maximo:
            raise DropItem("Resultado fuera de los primeros 10.")
        adaptador["precio"] = round(float(adaptador["precio"]), 2)
        adaptador.setdefault("formas_pago", [])
        adaptador.setdefault("formas_pago_internacional", [])
        adaptador.setdefault("descripcion", "")
        adaptador.setdefault("url_imagen", "")
        adaptador.setdefault("isbn", "")
        adaptador.setdefault("autor", "")
        return item


class FormasPagoPipeline(PipelineBase):
    """Arma la lista "forma de pago — precio".

    El sitio publica un único precio online para todos los medios de
    pago nacionales (en pesos) y el equivalente en dólares para los
    medios internacionales.
    """

    @staticmethod
    def _importe(valor: float) -> str:
        texto = f"{valor:,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")

    def process_item(self, item: Any, spider: Optional[Spider] = None) -> Any:
        adaptador = ItemAdapter(item)
        precio = self._importe(adaptador["precio"])
        formas = [f"{forma} — $ {precio}"
                  for forma in adaptador.get("formas_pago") or []]
        precio_usd = adaptador.get("precio_usd")
        if precio_usd:
            formas.extend(
                f"{forma} (exterior) — U$s {self._importe(precio_usd)}"
                for forma in adaptador.get("formas_pago_internacional") or [])
        if not formas:
            formas = [f"Precio online — $ {precio}"]
        adaptador["formas_pago"] = formas
        return item


class CoincidenciaPipeline(PipelineBase):
    """Calcula el puntaje de coincidencia con el libro del catálogo."""

    def process_item(self, item: Any, spider: Optional[Spider] = None) -> Any:
        spider = self._spider(spider)
        adaptador = ItemAdapter(item)
        libro = spider.catalogo.get(int(adaptador["libro_id"]))
        if libro is None:
            raise DropItem("El libro no pertenece a nuestro catálogo.")
        adaptador["coincidencia"] = puntaje_coincidencia(
            libro, adaptador["titulo"], adaptador.get("autor", ""),
            adaptador.get("isbn", ""))
        return item


class BaseDatosPipeline(PipelineBase):
    """Guarda los resultados en la base y elige el mejor de cada libro."""

    def __init__(self, crawler: Optional[Crawler] = None) -> None:
        super().__init__(crawler)
        self._conexion: Optional[ConexionDB] = None
        self._repositorio: Optional[RepositorioPrecioWeb] = None
        self._guardados: Dict[int, List[PrecioWeb]] = defaultdict(list)

    def open_spider(self, spider: Optional[Spider] = None) -> None:
        self._conexion = ConexionDB()
        self._conexion.crear_tablas()
        self._repositorio = Repositorios.desde_conexion(
            self._conexion).precios_web

    def process_item(self, item: Any, spider: Optional[Spider] = None) -> Any:
        adaptador = ItemAdapter(item)
        precio_web = PrecioWeb(
            libro_id=int(adaptador["libro_id"]),
            fecha_extraccion=adaptador["fecha_extraccion"],
            posicion=int(adaptador["posicion"]),
            titulo=adaptador["titulo"], url=adaptador["url"],
            precio=adaptador["precio"],
            precio_usd=adaptador.get("precio_usd"),
            url_imagen=adaptador.get("url_imagen", ""),
            formas_pago=adaptador.get("formas_pago", []),
            descripcion=adaptador.get("descripcion", ""),
            isbn=adaptador.get("isbn", ""),
            coincidencia=int(adaptador.get("coincidencia") or 0))
        assert self._repositorio is not None
        self._repositorio.crear(precio_web)
        self._guardados[precio_web.libro_id].append(precio_web)
        return item

    def close_spider(self, spider: Optional[Spider] = None) -> None:
        spider = self._spider(spider)
        assert self._repositorio is not None and self._conexion is not None
        seleccionados = 0
        for resultados in self._guardados.values():
            mejor = max(resultados,
                        key=lambda r: (r.coincidencia, -r.posicion))
            if mejor.coincidencia >= COINCIDENCIA_MINIMA:
                self._repositorio.marcar_seleccionado(mejor.id or 0)
                seleccionados += 1
        self._escribir_resumen(spider, seleccionados)
        self._conexion.cerrar()

    def _escribir_resumen(self, spider: Spider, seleccionados: int) -> None:
        """Deja un JSON con el resumen para el proceso que lanzó el spider."""
        ruta = spider.settings.get("RESUMEN_SCRAPING")
        if not ruta:
            return
        resumen = {
            "fecha_extraccion": spider.fecha_extraccion.isoformat(sep=" "),
            "libros_buscados": len(spider.catalogo),
            "libros_con_resultados": len(self._guardados),
            "libros_sin_resultados": sorted(set(spider.sin_resultados)),
            "resultados_guardados": sum(len(r) for r in
                                        self._guardados.values()),
            "libros_con_coincidencia": seleccionados,
        }
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        Path(ruta).write_text(json.dumps(resumen, ensure_ascii=False,
                                         indent=2), encoding="utf-8")
