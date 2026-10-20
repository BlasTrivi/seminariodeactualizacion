"""Item Loaders: limpian y normalizan los datos a medida que se extraen.

Cada campo del ``LibroCuspideItem`` tiene un procesador de entrada (que
se aplica a cada valor extraído) y uno de salida (que decide qué valor
queda en el item).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from itemloaders.processors import Identity, Join, MapCompose, TakeFirst
from scrapy.loader import ItemLoader

from book_manager.scraper.items import LibroCuspideItem

#: Si lo que sigue a ":" en una forma de pago es más largo que esto, es una
#: explicación (se descarta); si es corto es parte del nombre (tarjetas).
LARGO_MAXIMO_DETALLE_PAGO = 45


def limpiar_texto(valor: Any) -> Optional[str]:
    """Quita espacios repetidos, saltos de línea y espacios duros."""
    if valor is None:
        return None
    texto = re.sub(r"\s+", " ", str(valor).replace("\xa0", " ")).strip()
    return texto or None


def parsear_precio(valor: Any) -> Optional[float]:
    """Convierte un precio con formato argentino en número.

    ``"$ 73.499,00"`` -> ``73499.0``; ``"47,73"`` -> ``47.73``. Devuelve
    None para textos sin número (por ejemplo el símbolo ``$`` suelto).
    """
    texto = limpiar_texto(valor)
    if not texto:
        return None
    numero = re.sub(r"[^\d,.]", "", texto)
    if not re.search(r"\d", numero):
        return None
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    elif numero.count(".") > 1 or re.search(r"\.\d{3}$", numero):
        numero = numero.replace(".", "")
    try:
        importe = round(float(numero), 2)
    except ValueError:
        return None
    return importe if importe > 0 else None


def limpiar_forma_pago(valor: Any) -> Optional[str]:
    """Deja solo el nombre del medio de pago.

    ``"> MercadoPago"`` -> ``"MercadoPago"``;
    ``"> RapiPago o Pago Fácil: recibirás un cupón..."`` ->
    ``"RapiPago o Pago Fácil"``.
    """
    texto = limpiar_texto(valor)
    if not texto:
        return None
    texto = texto.lstrip(">-• ").strip()
    nombre, separador, detalle = texto.partition(":")
    if separador and len(detalle.strip()) > LARGO_MAXIMO_DETALLE_PAGO:
        texto = nombre.strip()
    return texto.rstrip(".").strip() or None


def solo_digitos(valor: Any) -> Optional[str]:
    """ISBN sin guiones ni espacios."""
    texto = re.sub(r"[^\dXx]", "", str(valor or ""))
    return texto.upper() or None


def url_absoluta(valor: Any, loader_context: dict) -> Optional[str]:
    """Convierte una URL relativa en absoluta usando la respuesta."""
    texto = limpiar_texto(valor)
    if not texto:
        return None
    respuesta = loader_context.get("response")
    return respuesta.urljoin(texto) if respuesta is not None else texto


class LibroCuspideLoader(ItemLoader):
    """Loader del ``LibroCuspideItem``."""

    default_item_class = LibroCuspideItem
    default_input_processor = MapCompose(limpiar_texto)
    default_output_processor = TakeFirst()

    precio_in = MapCompose(parsear_precio)
    precio_usd_in = MapCompose(parsear_precio)
    isbn_in = MapCompose(solo_digitos)
    url_in = MapCompose(url_absoluta)
    url_imagen_in = MapCompose(url_absoluta)
    formas_pago_in = MapCompose(limpiar_forma_pago)
    formas_pago_out = Identity()
    formas_pago_internacional_in = MapCompose(limpiar_forma_pago)
    formas_pago_internacional_out = Identity()
    descripcion_out = Join(" ")
