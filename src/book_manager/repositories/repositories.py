"""Repositorios: persistencia de las entidades en archivos CSV.

Se toman como base las interfaces propuestas en el enunciado
(``IRepositorio``, ``IRepositorioStock`` e ``IRepositorioCotizacionDolar``)
y se implementan sobre archivos CSV. Cada repositorio administra un único
archivo y ofrece el CRUD completo (Alta, Lectura, Modificación y Borrado).
"""
from __future__ import annotations

import abc
import csv
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any, Generic, Iterable, List, Optional, Type, TypeVar,
)

from book_manager.entities.entities import (
    CotizacionDolar, Editorial, EntidadBase, Genero, Libro, Moneda, Precio,
    Serializable, Stock, TipoCotizacion,
)

T = TypeVar("T", bound=EntidadBase)
S = TypeVar("S", bound=Serializable)


# ---------------------------------------------------------------------------
# Interfaces (base propuesta en el enunciado)
# ---------------------------------------------------------------------------

class IRepositorio(abc.ABC, Generic[T]):
    """Interfaz para repositorios que manejan entidades con CRUD básico."""

    @abc.abstractmethod
    def crear(self, entidad: T) -> T:
        """Crea una nueva entidad en el repositorio.

        Args:
            entidad (T): La entidad a crear.

        Returns:
            T: La entidad creada.

        Raises:
            ValueError: Si ya existe una entidad con el mismo ID.
        """

    @abc.abstractmethod
    def leer_por_id(self, id: int) -> Optional[T]:
        """Lee una entidad del repositorio por su ID.

        Args:
            id (int): El ID de la entidad a leer.

        Returns:
            Optional[T]: La entidad si se encuentra, None en caso contrario.
        """

    @abc.abstractmethod
    def leer_todos(self) -> List[T]:
        """Lee todas las entidades del repositorio.

        Returns:
            List[T]: Una lista de todas las entidades.
        """

    @abc.abstractmethod
    def actualizar(self, entidad: T) -> T:
        """Actualiza una entidad existente en el repositorio.

        Args:
            entidad (T): La entidad a actualizar (debe tener un ID existente).

        Returns:
            T: La entidad actualizada.

        Raises:
            ValueError: Si no se encuentra la entidad para actualizar.
        """

    @abc.abstractmethod
    def eliminar(self, id: int) -> bool:
        """Elimina una entidad del repositorio por su ID.

        Args:
            id (int): El ID de la entidad a eliminar.

        Returns:
            bool: True si la entidad fue eliminada, False si no se encontró.
        """


class IRepositorioStock(abc.ABC):
    """Interfaz para repositorios del tipo Stock."""

    @abc.abstractmethod
    def crear(self, stock: Stock) -> Stock:
        """Crea un nuevo registro de stock.

        Args:
            stock (Stock): El objeto Stock a crear.

        Returns:
            Stock: El objeto Stock creado.

        Raises:
            ValueError: Si ya existe un registro de stock para el mismo libro.
        """

    @abc.abstractmethod
    def leer_por_libro(self, libro_id: int) -> Optional[Stock]:
        """Lee un registro de stock por ID de libro.

        Args:
            libro_id (int): El ID del libro asociado al stock.

        Returns:
            Optional[Stock]: El objeto Stock si se encuentra, None si no.
        """

    @abc.abstractmethod
    def leer_todos(self) -> List[Stock]:
        """Lee todos los registros de stock.

        Returns:
            List[Stock]: Una lista con todos los registros de stock.
        """

    @abc.abstractmethod
    def actualizar(self, stock: Stock) -> Stock:
        """Actualiza un registro de stock existente.

        Args:
            stock (Stock): El objeto Stock a actualizar (con libro_id
                existente).

        Returns:
            Stock: El objeto Stock actualizado.

        Raises:
            ValueError: Si no se encuentra el stock para actualizar.
        """

    @abc.abstractmethod
    def eliminar(self, libro_id: int) -> bool:
        """Elimina un registro de stock por ID de libro.

        Args:
            libro_id (int): El ID del libro asociado al stock a eliminar.

        Returns:
            bool: True si el stock fue eliminado, False si no se encontró.
        """


class IRepositorioCotizacionDolar(abc.ABC):
    """Interfaz para repositorios del tipo CotizacionDolar."""

    @abc.abstractmethod
    def crear(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        """Crea una nueva cotización de dólar.

        Args:
            cotizacion (CotizacionDolar): El objeto CotizacionDolar a crear.

        Returns:
            CotizacionDolar: El objeto CotizacionDolar creado.

        Raises:
            ValueError: Si ya existe una cotización para el mismo tipo y
                fecha.
        """

    @abc.abstractmethod
    def leer_por_tipo_y_fecha(
            self, tipo_id: int,
            fecha: datetime.date) -> Optional[CotizacionDolar]:
        """Lee una cotización de dólar por tipo y fecha.

        Args:
            tipo_id (int): El ID del tipo de cotización.
            fecha (datetime.date): La fecha de la cotización.

        Returns:
            Optional[CotizacionDolar]: La cotización si se encuentra, None
                en caso contrario.
        """

    @abc.abstractmethod
    def leer_historico_por_tipo(self, tipo_id: int) -> List[CotizacionDolar]:
        """Lee el histórico de cotizaciones para un tipo específico.

        Args:
            tipo_id (int): El ID del tipo de cotización.

        Returns:
            List[CotizacionDolar]: Cotizaciones del tipo dado, ordenadas
                por fecha ascendente.
        """

    @abc.abstractmethod
    def leer_todos(self) -> List[CotizacionDolar]:
        """Lee todas las cotizaciones registradas.

        Returns:
            List[CotizacionDolar]: Una lista con todas las cotizaciones.
        """

    @abc.abstractmethod
    def actualizar(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        """Actualiza una cotización de dólar existente.

        Args:
            cotizacion (CotizacionDolar): El objeto CotizacionDolar a
                actualizar.

        Returns:
            CotizacionDolar: El objeto CotizacionDolar actualizado.

        Raises:
            ValueError: Si no se encuentra la cotización para actualizar.
        """

    @abc.abstractmethod
    def eliminar(self, tipo_id: int, fecha: datetime.date) -> bool:
        """Elimina una cotización de dólar por tipo y fecha.

        Args:
            tipo_id (int): El ID del tipo de cotización.
            fecha (datetime.date): La fecha de la cotización a eliminar.

        Returns:
            bool: True si la cotización fue eliminada, False si no se
                encontró.
        """


# ---------------------------------------------------------------------------
# Acceso al archivo CSV
# ---------------------------------------------------------------------------

class AlmacenCSV(Generic[S]):
    """Lee y escribe una lista de entidades en un archivo CSV."""

    def __init__(self, ruta: Path, clase: Type[S]) -> None:
        self._ruta = Path(ruta)
        self._clase = clase

    @property
    def ruta(self) -> Path:
        return self._ruta

    def existe(self) -> bool:
        return self._ruta.exists()

    def leer(self) -> List[S]:
        """Devuelve todas las filas del archivo convertidas a entidades."""
        if not self._ruta.exists():
            self.escribir([])
            return []
        with self._ruta.open(newline="", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            return [self._clase.desde_dict(fila) for fila in lector]

    def escribir(self, entidades: Iterable[S]) -> None:
        """Reemplaza el contenido del archivo con las entidades recibidas."""
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._ruta.open("w", newline="", encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=self._clase.CAMPOS,
                                      lineterminator="\n")
            escritor.writeheader()
            for entidad in entidades:
                escritor.writerow(entidad.a_dict())

    def vaciar(self) -> None:
        """Deja el archivo únicamente con el encabezado."""
        self.escribir([])


# ---------------------------------------------------------------------------
# Implementación genérica para entidades con id
# ---------------------------------------------------------------------------

class RepositorioCSV(IRepositorio[T]):
    """CRUD genérico sobre CSV para cualquier entidad con id."""

    def __init__(self, ruta: Path, clase: Type[T]) -> None:
        self._almacen: AlmacenCSV[T] = AlmacenCSV(ruta, clase)

    @property
    def ruta(self) -> Path:
        return self._almacen.ruta

    @staticmethod
    def _siguiente_id(entidades: List[T]) -> int:
        return max((e.id or 0 for e in entidades), default=0) + 1

    def crear(self, entidad: T) -> T:
        entidades = self._almacen.leer()
        if entidad.id is None:
            entidad.id = self._siguiente_id(entidades)
        elif any(e.id == entidad.id for e in entidades):
            raise ValueError(f"Ya existe un registro con id {entidad.id}.")
        entidades.append(entidad)
        self._almacen.escribir(entidades)
        return entidad

    def leer_por_id(self, id: int) -> Optional[T]:
        for entidad in self._almacen.leer():
            if entidad.id == id:
                return entidad
        return None

    def leer_todos(self) -> List[T]:
        return self._almacen.leer()

    def actualizar(self, entidad: T) -> T:
        entidades = self._almacen.leer()
        for posicion, existente in enumerate(entidades):
            if existente.id == entidad.id:
                entidades[posicion] = entidad
                self._almacen.escribir(entidades)
                return entidad
        raise ValueError(f"No existe un registro con id {entidad.id}.")

    def eliminar(self, id: int) -> bool:
        entidades = self._almacen.leer()
        restantes = [e for e in entidades if e.id != id]
        if len(restantes) == len(entidades):
            return False
        self._almacen.escribir(restantes)
        return True

    def vaciar(self) -> None:
        """Borra todos los registros (usado al recargar datos iniciales)."""
        self._almacen.vaciar()


class RepositorioGenero(RepositorioCSV[Genero]):
    """Persistencia de géneros literarios."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, Genero)

    def leer_por_nombre(self, nombre: str) -> Optional[Genero]:
        nombre = nombre.strip().lower()
        for genero in self.leer_todos():
            if genero.nombre.lower() == nombre:
                return genero
        return None


class RepositorioEditorial(RepositorioCSV[Editorial]):
    """Persistencia de editoriales."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, Editorial)

    def leer_por_nombre(self, nombre: str) -> Optional[Editorial]:
        nombre = nombre.strip().lower()
        for editorial in self.leer_todos():
            if editorial.nombre.lower() == nombre:
                return editorial
        return None


class RepositorioMoneda(RepositorioCSV[Moneda]):
    """Persistencia de monedas."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, Moneda)

    def leer_por_codigo(self, codigo: str) -> Optional[Moneda]:
        codigo = codigo.strip().upper()
        for moneda in self.leer_todos():
            if moneda.codigo == codigo:
                return moneda
        return None


class RepositorioTipoCotizacion(RepositorioCSV[TipoCotizacion]):
    """Persistencia de tipos de cotización del dólar."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, TipoCotizacion)

    def leer_por_nombre(self, nombre: str) -> Optional[TipoCotizacion]:
        nombre = nombre.strip().lower()
        for tipo in self.leer_todos():
            if tipo.nombre.lower() == nombre:
                return tipo
        return None


class RepositorioLibro(RepositorioCSV[Libro]):
    """Persistencia de libros."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, Libro)

    def leer_por_isbn(self, isbn: str) -> Optional[Libro]:
        isbn = isbn.replace("-", "").replace(" ", "")
        for libro in self.leer_todos():
            if libro.isbn == isbn:
                return libro
        return None

    def leer_por_genero(self, genero_id: int) -> List[Libro]:
        return [libro for libro in self.leer_todos()
                if libro.genero_id == genero_id]

    def leer_por_editorial(self, editorial_id: int) -> List[Libro]:
        return [libro for libro in self.leer_todos()
                if libro.editorial_id == editorial_id]

    def buscar_por_titulo(self, texto: str) -> List[Libro]:
        texto = texto.strip().lower()
        return [libro for libro in self.leer_todos()
                if texto in libro.titulo.lower()]


class RepositorioPrecio(RepositorioCSV[Precio]):
    """Persistencia de precios."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(ruta, Precio)

    def leer_por_libro(self, libro_id: int) -> List[Precio]:
        return [p for p in self.leer_todos() if p.libro_id == libro_id]

    def leer_por_moneda(self, moneda_id: int) -> List[Precio]:
        return [p for p in self.leer_todos() if p.moneda_id == moneda_id]

    def leer_por_libro_y_moneda(self, libro_id: int,
                                moneda_id: int) -> Optional[Precio]:
        for precio in self.leer_todos():
            if precio.libro_id == libro_id and precio.moneda_id == moneda_id:
                return precio
        return None

    def eliminar_por_libro(self, libro_id: int) -> int:
        """Elimina todos los precios de un libro y devuelve cuántos borró."""
        precios = self.leer_todos()
        restantes = [p for p in precios if p.libro_id != libro_id]
        eliminados = len(precios) - len(restantes)
        if eliminados:
            self._almacen.escribir(restantes)
        return eliminados


# ---------------------------------------------------------------------------
# Repositorios con clave natural (sin id)
# ---------------------------------------------------------------------------

class RepositorioStock(IRepositorioStock):
    """Persistencia de stock; la clave es el id del libro."""

    def __init__(self, ruta: Path) -> None:
        self._almacen: AlmacenCSV[Stock] = AlmacenCSV(ruta, Stock)

    @property
    def ruta(self) -> Path:
        return self._almacen.ruta

    def crear(self, stock: Stock) -> Stock:
        registros = self._almacen.leer()
        if any(r.libro_id == stock.libro_id for r in registros):
            raise ValueError(
                f"Ya existe stock para el libro {stock.libro_id}.")
        registros.append(stock)
        self._almacen.escribir(registros)
        return stock

    def leer_por_libro(self, libro_id: int) -> Optional[Stock]:
        for stock in self._almacen.leer():
            if stock.libro_id == libro_id:
                return stock
        return None

    def leer_todos(self) -> List[Stock]:
        return self._almacen.leer()

    def actualizar(self, stock: Stock) -> Stock:
        registros = self._almacen.leer()
        for posicion, existente in enumerate(registros):
            if existente.libro_id == stock.libro_id:
                registros[posicion] = stock
                self._almacen.escribir(registros)
                return stock
        raise ValueError(f"No existe stock para el libro {stock.libro_id}.")

    def eliminar(self, libro_id: int) -> bool:
        registros = self._almacen.leer()
        restantes = [r for r in registros if r.libro_id != libro_id]
        if len(restantes) == len(registros):
            return False
        self._almacen.escribir(restantes)
        return True

    def vaciar(self) -> None:
        self._almacen.vaciar()


class RepositorioCotizacionDolar(IRepositorioCotizacionDolar):
    """Persistencia de cotizaciones; la clave es (tipo_id, fecha)."""

    def __init__(self, ruta: Path) -> None:
        self._almacen: AlmacenCSV[CotizacionDolar] = AlmacenCSV(
            ruta, CotizacionDolar)

    @property
    def ruta(self) -> Path:
        return self._almacen.ruta

    def crear(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        registros = self._almacen.leer()
        if any(r.tipo_id == cotizacion.tipo_id and r.fecha == cotizacion.fecha
               for r in registros):
            raise ValueError(
                f"Ya existe una cotización del tipo {cotizacion.tipo_id} "
                f"para la fecha {cotizacion.fecha}.")
        registros.append(cotizacion)
        self._almacen.escribir(registros)
        return cotizacion

    def leer_por_tipo_y_fecha(
            self, tipo_id: int,
            fecha: datetime.date) -> Optional[CotizacionDolar]:
        for cotizacion in self._almacen.leer():
            if cotizacion.tipo_id == tipo_id and cotizacion.fecha == fecha:
                return cotizacion
        return None

    def leer_historico_por_tipo(self, tipo_id: int) -> List[CotizacionDolar]:
        historico = [c for c in self._almacen.leer() if c.tipo_id == tipo_id]
        return sorted(historico, key=lambda c: c.fecha)

    def leer_ultima_por_tipo(self, tipo_id: int) -> Optional[CotizacionDolar]:
        """Devuelve la cotización más reciente de un tipo, si existe."""
        historico = self.leer_historico_por_tipo(tipo_id)
        return historico[-1] if historico else None

    def leer_todos(self) -> List[CotizacionDolar]:
        return sorted(self._almacen.leer(), key=lambda c: (c.tipo_id, c.fecha))

    def actualizar(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        registros = self._almacen.leer()
        for posicion, existente in enumerate(registros):
            if (existente.tipo_id == cotizacion.tipo_id
                    and existente.fecha == cotizacion.fecha):
                registros[posicion] = cotizacion
                self._almacen.escribir(registros)
                return cotizacion
        raise ValueError(
            f"No existe una cotización del tipo {cotizacion.tipo_id} "
            f"para la fecha {cotizacion.fecha}.")

    def eliminar(self, tipo_id: int, fecha: datetime.date) -> bool:
        registros = self._almacen.leer()
        restantes = [r for r in registros
                     if not (r.tipo_id == tipo_id and r.fecha == fecha)]
        if len(restantes) == len(registros):
            return False
        self._almacen.escribir(restantes)
        return True

    def vaciar(self) -> None:
        self._almacen.vaciar()


# ---------------------------------------------------------------------------
# Contenedor con todos los repositorios del sistema
# ---------------------------------------------------------------------------

@dataclass
class Repositorios:
    """Agrupa los repositorios para pasarlos a la capa de servicios."""

    generos: RepositorioGenero
    editoriales: RepositorioEditorial
    monedas: RepositorioMoneda
    tipos_cotizacion: RepositorioTipoCotizacion
    libros: RepositorioLibro
    precios: RepositorioPrecio
    stock: RepositorioStock
    cotizaciones: RepositorioCotizacionDolar

    @classmethod
    def desde_directorio(cls, directorio: Path) -> "Repositorios":
        """Crea todos los repositorios apuntando a un directorio de CSV."""
        directorio = Path(directorio)
        directorio.mkdir(parents=True, exist_ok=True)
        return cls(
            generos=RepositorioGenero(directorio / "generos.csv"),
            editoriales=RepositorioEditorial(directorio / "editoriales.csv"),
            monedas=RepositorioMoneda(directorio / "monedas.csv"),
            tipos_cotizacion=RepositorioTipoCotizacion(
                directorio / "tipos_cotizacion.csv"),
            libros=RepositorioLibro(directorio / "libros.csv"),
            precios=RepositorioPrecio(directorio / "precios.csv"),
            stock=RepositorioStock(directorio / "stock.csv"),
            cotizaciones=RepositorioCotizacionDolar(
                directorio / "cotizaciones_dolar.csv"),
        )

    def todos(self) -> List[Any]:
        """Lista de repositorios, en el orden de carga de datos."""
        return [self.generos, self.editoriales, self.monedas,
                self.tipos_cotizacion, self.libros, self.precios,
                self.stock, self.cotizaciones]

    def archivos_existen(self) -> bool:
        """Indica si todos los archivos CSV ya fueron creados."""
        return all(Path(repo.ruta).exists() for repo in self.todos())
