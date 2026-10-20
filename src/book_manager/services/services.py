"""Servicios: lógica de negocio aplicada sobre cada operación del CRUD.

Los servicios reciben los repositorios por inyección de dependencias y se
encargan de las validaciones que no pertenecen a una sola entidad:
unicidad (nombres, códigos, ISBN), integridad referencial (que exista el
género, la editorial, la moneda, el libro...), borrados bloqueados o en
cascada y los reportes que combinan varias entidades.

Sprint 2:

- ``ServicioCotizacionDolar.obtener_cotizaciones`` consulta la API del
  dólar (URL en ``.env``), descarga las cotizaciones y las registra en la
  base de datos (Ejercicio 07).
- ``ServicioCotizador`` suma la lista de precios bimonetaria (pesos y
  otra moneda seleccionada) y la exportación a CSV de los precios en
  todas las monedas con cotización (Ejercicio 08).

Sprint 3:

- ``ServicioScraping`` ejecuta el scraper de Cúspide (Ejercicio 03).
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar

import requests

from book_manager.database.connection import variable_entorno
from book_manager.entities.entities import (
    CotizacionDolar, Editorial, EntidadBase, Genero, Libro, Moneda, Precio,
    PrecioWeb, Stock, TipoCotizacion,
)
from book_manager.repositories.repositories import (
    IRepositorio, RepositorioCotizacionDolar, RepositorioEditorial,
    RepositorioGenero, RepositorioLibro, RepositorioMoneda,
    RepositorioPrecio, RepositorioPrecioWeb, RepositorioStock,
    RepositorioTipoCotizacion, Repositorios,
)

T = TypeVar("T", bound=EntidadBase)

CODIGO_PESO = "ARS"
CODIGO_DOLAR = "USD"

#: Variables del ``.env`` con las URL de la API (Ejercicio 07).
VARIABLE_API_URL = "API_URL"
VARIABLE_API_URL_COTIZACIONES = "API_URL_COTIZACIONES"
TIEMPO_ESPERA_API = 15  # segundos

#: Carpetas del Sprint 3: código fuente y reportes generados.
CARPETA_PAQUETE = Path(__file__).resolve().parents[1]
CARPETA_SRC = CARPETA_PAQUETE.parent
CARPETA_REPORTES = CARPETA_PAQUETE / "reportes"
CARPETA_SCRAPER = CARPETA_PAQUETE / "scraper"
TIEMPO_MAXIMO_SCRAPING = 30 * 60  # segundos

#: Nombre que usa el sistema para cada "casa" de la API del dólar.
NOMBRES_CASAS_API: Dict[str, str] = {
    "oficial": "Oficial",
    "blue": "Blue",
    "bolsa": "MEP",
    "contadoconliqui": "CCL",
    "tarjeta": "Tarjeta",
    "mayorista": "Mayorista",
    "cripto": "Cripto",
}


# ---------------------------------------------------------------------------
# Servicio genérico
# ---------------------------------------------------------------------------

class ServicioBase(Generic[T]):
    """CRUD con validaciones. Las subclases redefinen los métodos hook."""

    nombre_entidad = "registro"

    def __init__(self, repositorio: IRepositorio[T]) -> None:
        self._repositorio = repositorio

    def listar(self) -> List[T]:
        return self._repositorio.leer_todos()

    def obtener(self, id: int) -> T:
        """Devuelve la entidad o lanza ValueError si no existe."""
        entidad = self._repositorio.leer_por_id(id)
        if entidad is None:
            raise ValueError(
                f"No existe {self.nombre_entidad} con id {id}.")
        return entidad

    def crear(self, entidad: T) -> T:
        self._validar(entidad)
        return self._repositorio.crear(entidad)

    def actualizar(self, entidad: T) -> T:
        if entidad.id is None:
            raise ValueError("La entidad a actualizar debe tener id.")
        self.obtener(entidad.id)
        self._validar(entidad)
        return self._repositorio.actualizar(entidad)

    def eliminar(self, id: int) -> bool:
        self._validar_eliminacion(id)
        return self._repositorio.eliminar(id)

    def _validar(self, entidad: T) -> None:
        """Hook: reglas de negocio previas a crear o actualizar."""

    def _validar_eliminacion(self, id: int) -> None:
        """Hook: reglas de negocio previas a eliminar."""

    def _validar_nombre_unico(self, entidad: T, nombre: str) -> None:
        """Comprueba que no exista otra entidad con el mismo nombre."""
        for existente in self.listar():
            mismo_nombre = getattr(existente, "nombre", "").lower()
            if mismo_nombre == nombre.lower() and existente.id != entidad.id:
                raise ValueError(f"Ya existe {self.nombre_entidad} con el "
                                 f"nombre '{nombre}'.")


# ---------------------------------------------------------------------------
# Servicios de catálogo
# ---------------------------------------------------------------------------

class ServicioGenero(ServicioBase[Genero]):
    """Reglas de negocio para géneros."""

    nombre_entidad = "un género"

    def __init__(self, repositorio: RepositorioGenero,
                 repo_libros: RepositorioLibro) -> None:
        super().__init__(repositorio)
        self._repo_libros = repo_libros

    def _validar(self, entidad: Genero) -> None:
        self._validar_nombre_unico(entidad, entidad.nombre)

    def _validar_eliminacion(self, id: int) -> None:
        cantidad = len(self._repo_libros.leer_por_genero(id))
        if cantidad:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} libro(s) del género.")


class ServicioEditorial(ServicioBase[Editorial]):
    """Reglas de negocio para editoriales."""

    nombre_entidad = "una editorial"

    def __init__(self, repositorio: RepositorioEditorial,
                 repo_libros: RepositorioLibro) -> None:
        super().__init__(repositorio)
        self._repo_libros = repo_libros

    def _validar(self, entidad: Editorial) -> None:
        self._validar_nombre_unico(entidad, entidad.nombre)

    def _validar_eliminacion(self, id: int) -> None:
        cantidad = len(self._repo_libros.leer_por_editorial(id))
        if cantidad:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} libro(s) de la "
                "editorial.")


class ServicioMoneda(ServicioBase[Moneda]):
    """Reglas de negocio para monedas."""

    nombre_entidad = "una moneda"

    def __init__(self, repositorio: RepositorioMoneda,
                 repo_precios: RepositorioPrecio,
                 repo_tipos: RepositorioTipoCotizacion) -> None:
        super().__init__(repositorio)
        self._repo_monedas = repositorio
        self._repo_precios = repo_precios
        self._repo_tipos = repo_tipos

    def obtener_por_codigo(self, codigo: str) -> Moneda:
        moneda = self._repo_monedas.leer_por_codigo(codigo)
        if moneda is None:
            raise ValueError(f"No existe la moneda '{codigo.upper()}'.")
        return moneda

    def _validar(self, entidad: Moneda) -> None:
        for existente in self.listar():
            if (existente.codigo == entidad.codigo
                    and existente.id != entidad.id):
                raise ValueError(
                    f"Ya existe una moneda con código {entidad.codigo}.")

    def _validar_eliminacion(self, id: int) -> None:
        cantidad = len(self._repo_precios.leer_por_moneda(id))
        if cantidad:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} precio(s) en esa "
                "moneda.")
        cantidad = len(self._repo_tipos.leer_por_moneda(id))
        if cantidad:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} tipo(s) de "
                "cotización de esa moneda.")


class ServicioTipoCotizacion(ServicioBase[TipoCotizacion]):
    """Reglas de negocio para tipos de cotización."""

    nombre_entidad = "un tipo de cotización"

    def __init__(self, repositorio: RepositorioTipoCotizacion,
                 repo_cotizaciones: RepositorioCotizacionDolar,
                 repo_monedas: RepositorioMoneda) -> None:
        super().__init__(repositorio)
        self._repo_tipos = repositorio
        self._repo_cotizaciones = repo_cotizaciones
        self._repo_monedas = repo_monedas

    def listar_por_moneda(self, moneda_id: int) -> List[TipoCotizacion]:
        return self._repo_tipos.leer_por_moneda(moneda_id)

    def _validar(self, entidad: TipoCotizacion) -> None:
        if self._repo_monedas.leer_por_id(entidad.moneda_id) is None:
            raise ValueError(
                f"No existe una moneda con id {entidad.moneda_id}.")
        existente = self._repo_tipos.leer_por_nombre(entidad.nombre,
                                                     entidad.moneda_id)
        if existente is not None and existente.id != entidad.id:
            raise ValueError(
                f"Ya existe el tipo de cotización '{entidad.nombre}' para "
                "esa moneda.")

    def _validar_eliminacion(self, id: int) -> None:
        cantidad = len(self._repo_cotizaciones.leer_historico_por_tipo(id))
        if cantidad:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} cotización(es) "
                "registradas de ese tipo.")


@dataclass
class LibroDetalle:
    """Libro junto con los objetos relacionados (relación entre objetos)."""

    libro: Libro
    genero: Optional[Genero]
    editorial: Optional[Editorial]
    precios: List[Precio]
    stock: Optional[Stock]


class ServicioLibro(ServicioBase[Libro]):
    """Reglas de negocio para libros."""

    nombre_entidad = "un libro"

    def __init__(self, repositorio: RepositorioLibro,
                 repo_generos: RepositorioGenero,
                 repo_editoriales: RepositorioEditorial,
                 repo_precios: RepositorioPrecio,
                 repo_stock: RepositorioStock) -> None:
        super().__init__(repositorio)
        self._repo_libros = repositorio
        self._repo_generos = repo_generos
        self._repo_editoriales = repo_editoriales
        self._repo_precios = repo_precios
        self._repo_stock = repo_stock

    def buscar_por_titulo(self, texto: str) -> List[Libro]:
        return self._repo_libros.buscar_por_titulo(texto)

    def obtener_detalle(self, id: int) -> LibroDetalle:
        """Arma el libro con su género, editorial, precios y stock."""
        libro = self.obtener(id)
        return LibroDetalle(
            libro=libro,
            genero=self._repo_generos.leer_por_id(libro.genero_id),
            editorial=self._repo_editoriales.leer_por_id(libro.editorial_id),
            precios=self._repo_precios.leer_por_libro(id),
            stock=self._repo_stock.leer_por_libro(id),
        )

    def _validar(self, entidad: Libro) -> None:
        if self._repo_generos.leer_por_id(entidad.genero_id) is None:
            raise ValueError(
                f"No existe un género con id {entidad.genero_id}.")
        if self._repo_editoriales.leer_por_id(entidad.editorial_id) is None:
            raise ValueError(
                f"No existe una editorial con id {entidad.editorial_id}.")
        existente = self._repo_libros.leer_por_isbn(entidad.isbn)
        if existente is not None and existente.id != entidad.id:
            raise ValueError(
                f"Ya existe un libro con ISBN {entidad.isbn}: "
                f"'{existente.titulo}'.")

    def eliminar(self, id: int) -> bool:
        """Elimina el libro y, en cascada, sus precios y su stock.

        Primero se borran los registros dependientes y luego el libro,
        de modo que las claves foráneas de la base nunca queden rotas.
        """
        self.obtener(id)
        self._repo_precios.eliminar_por_libro(id)
        self._repo_stock.eliminar(id)
        return self._repositorio.eliminar(id)


# ---------------------------------------------------------------------------
# Servicios de valuación
# ---------------------------------------------------------------------------

class ServicioPrecio(ServicioBase[Precio]):
    """Reglas de negocio para precios."""

    nombre_entidad = "un precio"

    def __init__(self, repositorio: RepositorioPrecio,
                 repo_libros: RepositorioLibro,
                 repo_monedas: RepositorioMoneda) -> None:
        super().__init__(repositorio)
        self._repo_precios = repositorio
        self._repo_libros = repo_libros
        self._repo_monedas = repo_monedas

    def listar_por_libro(self, libro_id: int) -> List[Precio]:
        return self._repo_precios.leer_por_libro(libro_id)

    def _validar(self, entidad: Precio) -> None:
        if self._repo_libros.leer_por_id(entidad.libro_id) is None:
            raise ValueError(f"No existe un libro con id {entidad.libro_id}.")
        if self._repo_monedas.leer_por_id(entidad.moneda_id) is None:
            raise ValueError(
                f"No existe una moneda con id {entidad.moneda_id}.")
        existente = self._repo_precios.leer_por_libro_y_moneda(
            entidad.libro_id, entidad.moneda_id)
        if existente is not None and existente.id != entidad.id:
            raise ValueError(
                "El libro ya tiene un precio en esa moneda "
                f"(id {existente.id}); modifíquelo en lugar de crear otro.")


class ServicioStock:
    """Reglas de negocio para el stock (clave: id de libro)."""

    def __init__(self, repositorio: RepositorioStock,
                 repo_libros: RepositorioLibro) -> None:
        self._repositorio = repositorio
        self._repo_libros = repo_libros

    def listar(self) -> List[Stock]:
        return self._repositorio.leer_todos()

    def obtener(self, libro_id: int) -> Stock:
        stock = self._repositorio.leer_por_libro(libro_id)
        if stock is None:
            raise ValueError(f"No hay stock cargado para el libro {libro_id}.")
        return stock

    def crear(self, stock: Stock) -> Stock:
        self._validar(stock)
        return self._repositorio.crear(stock)

    def actualizar(self, stock: Stock) -> Stock:
        self._validar(stock)
        return self._repositorio.actualizar(stock)

    def eliminar(self, libro_id: int) -> bool:
        return self._repositorio.eliminar(libro_id)

    def ingresar(self, libro_id: int, unidades: int) -> Stock:
        """Registra un ingreso de mercadería."""
        stock = self.obtener(libro_id)
        stock.ingresar(unidades)
        return self._repositorio.actualizar(stock)

    def egresar(self, libro_id: int, unidades: int) -> Stock:
        """Registra un egreso (por ejemplo, una venta)."""
        stock = self.obtener(libro_id)
        stock.egresar(unidades)
        return self._repositorio.actualizar(stock)

    def listar_bajo_minimo(self) -> List[Tuple[Libro, Stock]]:
        """Libros cuyo stock está por debajo del mínimo definido."""
        resultado: List[Tuple[Libro, Stock]] = []
        for stock in self.listar():
            if stock.esta_bajo_minimo():
                libro = self._repo_libros.leer_por_id(stock.libro_id)
                if libro is not None:
                    resultado.append((libro, stock))
        return resultado

    def _validar(self, stock: Stock) -> None:
        if self._repo_libros.leer_por_id(stock.libro_id) is None:
            raise ValueError(f"No existe un libro con id {stock.libro_id}.")


# ---------------------------------------------------------------------------
# Cotizaciones: CRUD + consulta a la API externa (Ejercicio 07)
# ---------------------------------------------------------------------------

@dataclass
class CotizacionImportada:
    """Resultado de registrar una cotización descargada de la API."""

    moneda: Moneda
    tipo: TipoCotizacion
    cotizacion: CotizacionDolar
    nueva: bool  # True si se creó, False si se actualizó la del día


class ClienteCotizacionesAPI:
    """Descarga las cotizaciones publicadas por la API (dolarapi.com).

    Las URL se leen del archivo ``.env`` (``API_URL`` para los distintos
    tipos de dólar y, opcionalmente, ``API_URL_COTIZACIONES`` para las
    demás monedas). Cada registro devuelto tiene las claves ``moneda``,
    ``casa``, ``nombre``, ``compra``, ``venta`` y ``fechaActualizacion``.
    """

    def __init__(self, url: Optional[str] = None,
                 url_cotizaciones: Optional[str] = None) -> None:
        self._url = url or variable_entorno(VARIABLE_API_URL)
        self._url_cotizaciones = url_cotizaciones or variable_entorno(
            VARIABLE_API_URL_COTIZACIONES, "")

    @property
    def url(self) -> str:
        return self._url

    @staticmethod
    def _descargar(url: str) -> List[Dict[str, Any]]:
        try:
            respuesta = requests.get(url, timeout=TIEMPO_ESPERA_API)
            respuesta.raise_for_status()
            datos = respuesta.json()
        except requests.RequestException as error:
            raise ValueError(
                f"No se pudo consultar la API ({url}): {error}") from error
        except ValueError as error:
            raise ValueError(
                f"La API ({url}) no devolvió un JSON válido.") from error
        if isinstance(datos, dict):
            datos = [datos]
        if not isinstance(datos, list):
            raise ValueError(f"Respuesta inesperada de la API ({url}).")
        return datos

    def buscar_dolares(self) -> List[Dict[str, Any]]:
        """Cotizaciones del dólar por casa (API_URL)."""
        return self._descargar(self._url)

    def buscar_otras_monedas(self) -> List[Dict[str, Any]]:
        """Cotizaciones de otras monedas (vacío si no está configurada)."""
        if not self._url_cotizaciones:
            return []
        registros = self._descargar(self._url_cotizaciones)
        return [registro for registro in registros
                if str(registro.get("moneda", "")).upper() != CODIGO_DOLAR]


class ServicioCotizacionDolar:
    """Reglas de negocio para cotizaciones (clave: tipo y fecha)."""

    def __init__(self, repositorio: RepositorioCotizacionDolar,
                 repo_tipos: RepositorioTipoCotizacion,
                 repo_monedas: RepositorioMoneda,
                 cliente_api: Optional[ClienteCotizacionesAPI] = None
                 ) -> None:
        self._repositorio = repositorio
        self._repo_tipos = repo_tipos
        self._repo_monedas = repo_monedas
        self._cliente_api = cliente_api

    # -- CRUD -------------------------------------------------------------

    def listar(self) -> List[CotizacionDolar]:
        return self._repositorio.leer_todos()

    def listar_por_tipo(self, tipo_id: int) -> List[CotizacionDolar]:
        return self._repositorio.leer_historico_por_tipo(tipo_id)

    def obtener(self, tipo_id: int,
                fecha: datetime.date) -> CotizacionDolar:
        cotizacion = self._repositorio.leer_por_tipo_y_fecha(tipo_id, fecha)
        if cotizacion is None:
            raise ValueError(
                f"No hay cotización del tipo {tipo_id} para {fecha}.")
        return cotizacion

    def obtener_ultima(self, tipo_id: int) -> CotizacionDolar:
        """Cotización más reciente de un tipo; falla si no hay ninguna."""
        if self._repo_tipos.leer_por_id(tipo_id) is None:
            raise ValueError(
                f"No existe un tipo de cotización con id {tipo_id}.")
        cotizacion = self._repositorio.leer_ultima_por_tipo(tipo_id)
        if cotizacion is None:
            raise ValueError(
                f"No hay cotizaciones cargadas para el tipo {tipo_id}.")
        return cotizacion

    def crear(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        self._validar(cotizacion)
        return self._repositorio.crear(cotizacion)

    def actualizar(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        self._validar(cotizacion)
        return self._repositorio.actualizar(cotizacion)

    def eliminar(self, tipo_id: int, fecha: datetime.date) -> bool:
        return self._repositorio.eliminar(tipo_id, fecha)

    def _validar(self, cotizacion: CotizacionDolar) -> None:
        if self._repo_tipos.leer_por_id(cotizacion.tipo_id) is None:
            raise ValueError(
                f"No existe un tipo de cotización con id "
                f"{cotizacion.tipo_id}.")
        if cotizacion.fecha > datetime.date.today():
            raise ValueError("La fecha de la cotización no puede ser futura.")
        if cotizacion.compra > cotizacion.venta:
            raise ValueError(
                "El valor de compra no puede superar al de venta.")

    # -- API externa (Ejercicio 07) ---------------------------------------

    @property
    def cliente_api(self) -> ClienteCotizacionesAPI:
        if self._cliente_api is None:
            self._cliente_api = ClienteCotizacionesAPI()
        return self._cliente_api

    def obtener_cotizaciones(self) -> List[CotizacionImportada]:
        """Busca, descarga y registra en la base las cotizaciones de la API.

        Para cada registro devuelto por la API se resuelve la moneda (se
        crea si no existe), el tipo de cotización (idem) y se guarda la
        cotización del día: si ya había una para ese tipo y fecha se
        actualiza con los valores nuevos.

        Returns:
            List[CotizacionImportada]: Una entrada por cotización
                registrada, indicando si fue alta o modificación.

        Raises:
            ValueError: Si la API no responde o devuelve datos inválidos.
        """
        registros = self.cliente_api.buscar_dolares()
        registros.extend(self.cliente_api.buscar_otras_monedas())
        importadas: List[CotizacionImportada] = []
        for registro in registros:
            importada = self._registrar_desde_api(registro)
            if importada is not None:
                importadas.append(importada)
        if not importadas:
            raise ValueError("La API no devolvió cotizaciones válidas.")
        return importadas

    def _registrar_desde_api(
            self, registro: Dict[str, Any]) -> Optional[CotizacionImportada]:
        """Convierte un registro de la API en una cotización persistida."""
        venta = registro.get("venta")
        if venta is None:
            return None  # sin precio de venta no hay cotización utilizable
        compra = registro.get("compra")
        if compra is None or float(compra) > float(venta):
            compra = venta
        moneda = self._moneda_desde_api(registro)
        tipo = self._tipo_desde_api(registro, moneda)
        fecha = self._fecha_desde_api(registro.get("fechaActualizacion"))
        cotizacion = CotizacionDolar(tipo.id or 0, fecha, float(compra),
                                     float(venta))
        existente = self._repositorio.leer_por_tipo_y_fecha(
            cotizacion.tipo_id, fecha)
        if existente is None:
            self.crear(cotizacion)
        else:
            self.actualizar(cotizacion)
        return CotizacionImportada(moneda, tipo, cotizacion,
                                   nueva=existente is None)

    def _moneda_desde_api(self, registro: Dict[str, Any]) -> Moneda:
        codigo = str(registro.get("moneda") or CODIGO_DOLAR).upper()
        moneda = self._repo_monedas.leer_por_codigo(codigo)
        if moneda is None:
            nombre = str(registro.get("nombre") or codigo)
            moneda = self._repo_monedas.crear(Moneda(codigo, nombre, ""))
        return moneda

    def _tipo_desde_api(self, registro: Dict[str, Any],
                        moneda: Moneda) -> TipoCotizacion:
        casa = str(registro.get("casa") or "").strip().lower()
        if moneda.codigo == CODIGO_DOLAR:
            nombre = NOMBRES_CASAS_API.get(
                casa, str(registro.get("nombre") or casa or "API"))
        else:
            nombre = casa.capitalize() or "Oficial"
        tipo = self._repo_tipos.leer_por_nombre(nombre, moneda.id)
        if tipo is None:
            descripcion = f"{registro.get('nombre', nombre)} (importado " \
                          f"desde la API, casa '{casa}')"
            tipo = self._repo_tipos.crear(
                TipoCotizacion(nombre, descripcion, moneda.id or 0))
        return tipo

    @staticmethod
    def _fecha_desde_api(valor: Optional[str]) -> datetime.date:
        """Convierte ``2026-10-08T18:00:00.000Z`` en una fecha local."""
        if not valor:
            return datetime.date.today()
        texto = str(valor).replace("Z", "+00:00")
        try:
            instante = datetime.datetime.fromisoformat(texto)
        except ValueError:
            return datetime.date.today()
        if instante.tzinfo is not None:
            instante = instante.astimezone()
        fecha = instante.date()
        return min(fecha, datetime.date.today())


# ---------------------------------------------------------------------------
# Reportes: valuación del catálogo según la cotización elegida
# ---------------------------------------------------------------------------

@dataclass
class LibroCotizado:
    """Resultado de cotizar un libro con un tipo de dólar."""

    libro: Libro
    precio: Precio
    moneda: Moneda
    cotizacion: CotizacionDolar
    valor_ars: float
    valor_usd: float


@dataclass
class PrecioBimonetario:
    """Precio de un libro en pesos y en otra moneda seleccionada."""

    libro: Libro
    precio: Precio
    moneda_lista: Moneda
    valor_ars: float
    moneda: Moneda
    tipo: TipoCotizacion
    cotizacion: CotizacionDolar
    valor_moneda: float


@dataclass
class ColumnaMoneda:
    """Una moneda/tipo con cotización vigente, usada en la exportación."""

    moneda: Moneda
    tipo: TipoCotizacion
    cotizacion: CotizacionDolar

    @property
    def encabezado(self) -> str:
        return f"{self.moneda.codigo}_{self.tipo.nombre}".replace(" ", "_")


class ServicioCotizador:
    """Convierte los precios de los libros entre pesos y otras monedas."""

    def __init__(self, libros: ServicioLibro, precios: ServicioPrecio,
                 monedas: ServicioMoneda, stock: ServicioStock,
                 tipos: ServicioTipoCotizacion,
                 cotizaciones: ServicioCotizacionDolar) -> None:
        self._libros = libros
        self._precios = precios
        self._monedas = monedas
        self._stock = stock
        self._tipos = tipos
        self._cotizaciones = cotizaciones

    # -- reportes del Sprint 1 --------------------------------------------

    def cotizar_libro(self, libro_id: int, tipo_id: int) -> LibroCotizado:
        """Valúa un libro en ARS y USD usando la última cotización del tipo.

        Se toma el precio en USD si existe; en caso contrario el precio en
        ARS. Cualquier otra moneda de lista no puede cotizarse.
        """
        libro = self._libros.obtener(libro_id)
        cotizacion = self._cotizacion_dolar(tipo_id)
        return self._cotizar(libro, cotizacion)

    def catalogo_valuado(self, tipo_id: int) -> List[LibroCotizado]:
        """Cotiza todos los libros que tengan precio en ARS o USD."""
        cotizacion = self._cotizacion_dolar(tipo_id)
        resultado: List[LibroCotizado] = []
        for libro in self._libros.listar():
            try:
                resultado.append(self._cotizar(libro, cotizacion))
            except ValueError:
                continue  # libro sin precio cotizable: se omite del listado
        return resultado

    def valor_inventario(self, tipo_id: int) -> Tuple[float, float]:
        """Suma precio x cantidad en stock para todo el catálogo."""
        total_ars = 0.0
        total_usd = 0.0
        for cotizado in self.catalogo_valuado(tipo_id):
            try:
                cantidad = self._stock.obtener(cotizado.libro.id or 0).cantidad
            except ValueError:
                cantidad = 0
            total_ars += cotizado.valor_ars * cantidad
            total_usd += cotizado.valor_usd * cantidad
        return round(total_ars, 2), round(total_usd, 2)

    # -- reportes del Sprint 2 (Ejercicio 08) -----------------------------

    def monedas_con_cotizacion(self) -> List[ColumnaMoneda]:
        """Monedas (distintas del peso) que tienen al menos una cotización.

        Devuelve una entrada por cada tipo de cotización con datos, con
        la cotización más reciente de ese tipo.
        """
        columnas: List[ColumnaMoneda] = []
        for moneda in self._monedas.listar():
            if moneda.codigo == CODIGO_PESO:
                continue
            for tipo in self._tipos.listar_por_moneda(moneda.id or 0):
                try:
                    cotizacion = self._cotizaciones.obtener_ultima(
                        tipo.id or 0)
                except ValueError:
                    continue
                columnas.append(ColumnaMoneda(moneda, tipo, cotizacion))
        return columnas

    def lista_precios_bimonetaria(self, tipo_dolar_id: int,
                                  tipo_moneda_id: int
                                  ) -> List[PrecioBimonetario]:
        """Lista de precios en pesos y en la moneda del tipo seleccionado.

        Args:
            tipo_dolar_id (int): Tipo de dólar con el que se pasan a pesos
                los libros cuyo precio de lista está en USD.
            tipo_moneda_id (int): Tipo de cotización (de cualquier moneda)
                en el que se expresa la segunda columna.

        Returns:
            List[PrecioBimonetario]: Un registro por libro cotizable.
        """
        tipo = self._tipos.obtener(tipo_moneda_id)
        moneda = self._monedas.obtener(tipo.moneda_id)
        cotizacion = self._cotizaciones.obtener_ultima(tipo_moneda_id)
        resultado: List[PrecioBimonetario] = []
        for cotizado in self.catalogo_valuado(tipo_dolar_id):
            resultado.append(PrecioBimonetario(
                libro=cotizado.libro, precio=cotizado.precio,
                moneda_lista=cotizado.moneda, valor_ars=cotizado.valor_ars,
                moneda=moneda, tipo=tipo, cotizacion=cotizacion,
                valor_moneda=round(cotizado.valor_ars / cotizacion.venta, 2)))
        return resultado

    def exportar_precios_csv(self, ruta: Path,
                             tipo_dolar_id: int) -> Tuple[Path, int, int]:
        """Exporta los precios en pesos y en todas las monedas con cotización.

        Args:
            ruta (Path): Archivo CSV de destino (se crea la carpeta).
            tipo_dolar_id (int): Tipo de dólar para pasar a pesos los
                libros con precio de lista en USD.

        Returns:
            Tuple[Path, int, int]: Ruta escrita, cantidad de libros y
                cantidad de columnas de moneda exportadas.
        """
        columnas = self.monedas_con_cotizacion()
        if not columnas:
            raise ValueError(
                "No hay cotizaciones registradas: obtenga las cotizaciones "
                "por API o cargue alguna manualmente.")
        catalogo = self.catalogo_valuado(tipo_dolar_id)
        encabezados = ["id", "isbn", "titulo", "autor", "moneda_lista",
                       "precio_lista", CODIGO_PESO]
        encabezados.extend(columna.encabezado for columna in columnas)
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo, lineterminator="\n")
            escritor.writerow(encabezados)
            escritor.writerow(self._fila_cotizaciones(columnas))
            for cotizado in catalogo:
                fila: List[object] = [
                    cotizado.libro.id, cotizado.libro.isbn,
                    cotizado.libro.titulo, cotizado.libro.autor,
                    cotizado.moneda.codigo, f"{cotizado.precio.valor:.2f}",
                    f"{cotizado.valor_ars:.2f}"]
                fila.extend(
                    f"{cotizado.valor_ars / columna.cotizacion.venta:.2f}"
                    for columna in columnas)
                escritor.writerow(fila)
        return ruta, len(catalogo), len(columnas)

    @staticmethod
    def _fila_cotizaciones(columnas: Sequence[ColumnaMoneda]) -> List[object]:
        """Fila informativa con la cotización (venta) usada en cada columna."""
        fila: List[object] = ["", "", "Cotización de venta utilizada", "",
                              "", "", "1.00"]
        fila.extend(f"{columna.cotizacion.venta:.2f}" for columna in columnas)
        return fila

    # -- internos ---------------------------------------------------------

    def _cotizacion_dolar(self, tipo_id: int) -> CotizacionDolar:
        """Última cotización de un tipo que debe pertenecer al dólar."""
        tipo = self._tipos.obtener(tipo_id)
        moneda = self._monedas.obtener(tipo.moneda_id)
        if moneda.codigo != CODIGO_DOLAR:
            raise ValueError(
                f"El tipo '{tipo.nombre}' corresponde a {moneda.codigo}; "
                "para valuar en pesos se necesita un tipo de dólar.")
        return self._cotizaciones.obtener_ultima(tipo_id)

    def _cotizar(self, libro: Libro,
                 cotizacion: CotizacionDolar) -> LibroCotizado:
        precio, moneda = self._precio_base(libro.id or 0)
        if moneda.codigo == CODIGO_DOLAR:
            valor_usd = precio.valor
            valor_ars = round(precio.valor * cotizacion.venta, 2)
        else:
            valor_ars = precio.valor
            valor_usd = round(precio.valor / cotizacion.venta, 2)
        return LibroCotizado(libro, precio, moneda, cotizacion,
                             valor_ars, valor_usd)

    def _precio_base(self, libro_id: int) -> Tuple[Precio, Moneda]:
        """Precio en USD si existe, si no en ARS; si no hay, ValueError."""
        precios = self._precios.listar_por_libro(libro_id)
        if not precios:
            raise ValueError(f"El libro {libro_id} no tiene precio cargado.")
        candidatos: Dict[str, Tuple[Precio, Moneda]] = {}
        for precio in precios:
            moneda = self._monedas.obtener(precio.moneda_id)
            candidatos[moneda.codigo] = (precio, moneda)
        for codigo in (CODIGO_DOLAR, CODIGO_PESO):
            if codigo in candidatos:
                return candidatos[codigo]
        raise ValueError(
            f"El libro {libro_id} solo tiene precios en monedas que no se "
            "pueden cotizar (se admiten ARS y USD).")


# ---------------------------------------------------------------------------
# Sprint 3 - Ejercicio 03: scraping de precios de la competencia
# ---------------------------------------------------------------------------

@dataclass
class ResultadoScraping:
    """Resumen de una ejecución del scraper."""

    fecha_extraccion: datetime.datetime
    libros_buscados: int
    libros_con_resultados: int
    libros_sin_resultados: List[int]
    resultados_guardados: int
    libros_con_coincidencia: int
    archivo_resultados: Path
    segundos: float

    def __str__(self) -> str:
        return (f"Scraping del {self.fecha_extraccion}: "
                f"{self.libros_buscados} libro(s) buscados, "
                f"{self.resultados_guardados} resultado(s) guardados, "
                f"{self.libros_con_coincidencia} libro(s) encontrados "
                f"({self.segundos:.0f} s).")


class ServicioScraping(ServicioBase[PrecioWeb]):
    """CRUD de los precios web y ejecución del ``CuspideSpider``."""

    nombre_entidad = "un precio web"

    def __init__(self, repositorio: RepositorioPrecioWeb,
                 repo_libros: RepositorioLibro,
                 carpeta_salida: Path = CARPETA_REPORTES / "scraping"
                 ) -> None:
        super().__init__(repositorio)
        self._repo_web = repositorio
        self._repo_libros = repo_libros
        self._carpeta_salida = Path(carpeta_salida)

    def _validar(self, entidad: PrecioWeb) -> None:
        if self._repo_libros.leer_por_id(entidad.libro_id) is None:
            raise ValueError(f"No existe un libro con id {entidad.libro_id}.")

    # -- consultas ----------------------------------------------------------

    def ultima_fecha_extraccion(self) -> datetime.datetime:
        """Fecha de la última ejecución; falla si nunca se ejecutó."""
        fecha = self._repo_web.ultima_fecha_extraccion()
        if fecha is None:
            raise ValueError("Todavía no se ejecutó el scraping: use la "
                             "opción 'Ejecutar scraping'.")
        return fecha

    def resultados(self, fecha: Optional[datetime.datetime] = None
                   ) -> List[PrecioWeb]:
        """Todos los resultados de una ejecución (por defecto la última)."""
        return self._repo_web.leer_por_fecha(
            fecha or self.ultima_fecha_extraccion())

    def seleccionados(self, fecha: Optional[datetime.datetime] = None
                      ) -> List[PrecioWeb]:
        """Resultado elegido para cada libro en una ejecución."""
        return self._repo_web.leer_seleccionados(
            fecha or self.ultima_fecha_extraccion())

    # -- ejecución del spider -----------------------------------------------

    def ejecutar_scraping(self, libros_ids: Optional[Sequence[int]] = None
                          ) -> ResultadoScraping:
        """Ejecuta el ``CuspideSpider`` y devuelve el resumen.

        El spider corre en un proceso separado (ver ``scraper/runner.py``)
        para poder ejecutarlo varias veces en la misma sesión. Los
        resultados quedan en la tabla ``precios_web`` y en un JSON dentro
        de ``reportes/scraping``.

        Args:
            libros_ids (Optional[Sequence[int]]): Libros a buscar; por
                defecto, todo el catálogo.

        Raises:
            ValueError: Si el catálogo está vacío o el scraper falla.
        """
        if not self._repo_libros.leer_todos():
            raise ValueError("No hay libros en el catálogo para buscar.")
        fecha = datetime.datetime.now().replace(microsecond=0)
        sello = fecha.strftime("%Y%m%d_%H%M%S")
        self._carpeta_salida.mkdir(parents=True, exist_ok=True)
        archivo_resumen = self._carpeta_salida / f"resumen_{sello}.json"
        archivo_resultados = self._carpeta_salida / f"cuspide_{sello}.json"
        comando = [sys.executable, "-m", "book_manager.scraper.runner",
                   "--resumen", str(archivo_resumen),
                   "--resultados", str(archivo_resultados),
                   "--fecha", fecha.isoformat(sep=" ")]
        if libros_ids:
            comando += ["--libros", ",".join(str(i) for i in libros_ids)]
        entorno = dict(os.environ)
        entorno["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(CARPETA_SRC), entorno.get("PYTHONPATH")]))
        inicio = time.monotonic()
        proceso = subprocess.run(
            comando, cwd=CARPETA_SCRAPER, env=entorno, capture_output=True,
            text=True, timeout=TIEMPO_MAXIMO_SCRAPING, check=False)
        if proceso.returncode != 0 or not archivo_resumen.exists():
            detalle = (proceso.stderr or proceso.stdout).strip()[-1500:]
            raise ValueError(f"El scraper terminó con error:\n{detalle}")
        datos = json.loads(archivo_resumen.read_text(encoding="utf-8"))
        return ResultadoScraping(
            fecha_extraccion=fecha,
            libros_buscados=int(datos["libros_buscados"]),
            libros_con_resultados=int(datos["libros_con_resultados"]),
            libros_sin_resultados=list(datos["libros_sin_resultados"]),
            resultados_guardados=int(datos["resultados_guardados"]),
            libros_con_coincidencia=int(datos["libros_con_coincidencia"]),
            archivo_resultados=archivo_resultados,
            segundos=round(time.monotonic() - inicio, 1))


# ---------------------------------------------------------------------------
# Contenedor con todos los servicios del sistema
# ---------------------------------------------------------------------------

@dataclass
class Servicios:
    """Agrupa los servicios para pasarlos a la interfaz de usuario."""

    generos: ServicioGenero
    editoriales: ServicioEditorial
    monedas: ServicioMoneda
    tipos_cotizacion: ServicioTipoCotizacion
    libros: ServicioLibro
    precios: ServicioPrecio
    stock: ServicioStock
    cotizaciones: ServicioCotizacionDolar
    cotizador: ServicioCotizador
    scraping: ServicioScraping

    @classmethod
    def desde_repositorios(cls, repos: Repositorios) -> "Servicios":
        """Construye todos los servicios inyectando los repositorios."""
        libros = ServicioLibro(repos.libros, repos.generos,
                               repos.editoriales, repos.precios, repos.stock)
        precios = ServicioPrecio(repos.precios, repos.libros, repos.monedas)
        monedas = ServicioMoneda(repos.monedas, repos.precios,
                                 repos.tipos_cotizacion)
        tipos = ServicioTipoCotizacion(repos.tipos_cotizacion,
                                       repos.cotizaciones, repos.monedas)
        stock = ServicioStock(repos.stock, repos.libros)
        cotizaciones = ServicioCotizacionDolar(
            repos.cotizaciones, repos.tipos_cotizacion, repos.monedas)
        return cls(
            generos=ServicioGenero(repos.generos, repos.libros),
            editoriales=ServicioEditorial(repos.editoriales, repos.libros),
            monedas=monedas,
            tipos_cotizacion=tipos,
            libros=libros,
            precios=precios,
            stock=stock,
            cotizaciones=cotizaciones,
            cotizador=ServicioCotizador(libros, precios, monedas, stock,
                                        tipos, cotizaciones),
            scraping=ServicioScraping(repos.precios_web, repos.libros),
        )
