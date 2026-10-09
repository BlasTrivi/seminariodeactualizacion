"""Repositorios: persistencia de las entidades en la base de datos.

Se mantienen las interfaces del enunciado (``IRepositorio``,
``IRepositorioStock`` e ``IRepositorioCotizacionDolar``) y la firma de
todos los métodos que usaban los servicios en el Sprint 1, pero la
implementación pasa de archivos CSV a tablas relacionales mediante
SQLAlchemy. Cada operación se ejecuta dentro del context manager de
transacciones de ``ConexionDB`` (Ejercicio 03).

Las entidades del dominio siguen siendo las clases de ``entities.py``;
cada repositorio sabe convertir entidad <-> modelo ORM.
"""
from __future__ import annotations

import abc
import datetime
from dataclasses import dataclass
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from book_manager.database.connection import ConexionDB
from book_manager.entities.entities import (
    CotizacionDolar, Editorial, EntidadBase, Genero, Libro, Moneda, Precio,
    Stock, TipoCotizacion,
)
from book_manager.models.models import (
    Base, CotizacionModel, EditorialModel, GeneroModel, LibroModel,
    MonedaModel, PrecioModel, StockModel, TipoCotizacionModel,
)

T = TypeVar("T", bound=EntidadBase)
M = TypeVar("M", bound=Base)


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
        """Crea una nueva cotización.

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
        """Lee una cotización por tipo y fecha.

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
        """Actualiza una cotización existente.

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
        """Elimina una cotización por tipo y fecha.

        Args:
            tipo_id (int): El ID del tipo de cotización.
            fecha (datetime.date): La fecha de la cotización a eliminar.

        Returns:
            bool: True si la cotización fue eliminada, False si no se
                encontró.
        """


# ---------------------------------------------------------------------------
# Implementación genérica sobre SQLAlchemy para entidades con id
# ---------------------------------------------------------------------------

class RepositorioSQL(IRepositorio[T], Generic[T, M]):
    """CRUD genérico sobre la base de datos para entidades con id.

    Las subclases indican el modelo ORM (``modelo``) y definen las dos
    conversiones: ``_volcar`` (entidad -> columnas del modelo) y
    ``_a_entidad`` (modelo -> entidad).
    """

    #: Modelo ORM (tabla) que administra el repositorio.
    modelo: Type[M]

    def __init__(self, conexion: ConexionDB) -> None:
        self._conexion = conexion

    @property
    def conexion(self) -> ConexionDB:
        return self._conexion

    # -- conversiones (hooks) ---------------------------------------------

    @abc.abstractmethod
    def _volcar(self, entidad: T, modelo: M) -> None:
        """Copia los atributos de la entidad en el modelo ORM."""

    @abc.abstractmethod
    def _a_entidad(self, modelo: M) -> T:
        """Construye la entidad del dominio a partir del modelo ORM."""

    # -- CRUD -------------------------------------------------------------

    def _siguiente_id(self, sesion: Session) -> int:
        """Próximo id disponible (independiente del motor de base de datos)."""
        maximo = sesion.execute(select(func.max(self.modelo.id))).scalar()
        return int(maximo or 0) + 1

    def crear(self, entidad: T) -> T:
        with self._conexion.transaccion() as sesion:
            if entidad.id is None:
                entidad.id = self._siguiente_id(sesion)
            elif sesion.get(self.modelo, entidad.id) is not None:
                raise ValueError(
                    f"Ya existe un registro con id {entidad.id}.")
            registro = self.modelo()
            self._volcar(entidad, registro)
            registro.id = entidad.id
            sesion.add(registro)
        return entidad

    def leer_por_id(self, id: int) -> Optional[T]:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(self.modelo, id)
            return None if registro is None else self._a_entidad(registro)

    def leer_todos(self) -> List[T]:
        with self._conexion.transaccion() as sesion:
            consulta = select(self.modelo).order_by(self.modelo.id)
            return [self._a_entidad(r) for r in sesion.scalars(consulta)]

    def actualizar(self, entidad: T) -> T:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(self.modelo, entidad.id)
            if registro is None:
                raise ValueError(
                    f"No existe un registro con id {entidad.id}.")
            self._volcar(entidad, registro)
        return entidad

    def eliminar(self, id: int) -> bool:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(self.modelo, id)
            if registro is None:
                return False
            sesion.delete(registro)
            return True

    def contar(self) -> int:
        """Cantidad de registros en la tabla."""
        with self._conexion.transaccion() as sesion:
            return int(sesion.execute(
                select(func.count()).select_from(self.modelo)).scalar() or 0)

    def vaciar(self) -> None:
        """Borra todos los registros (usado al recargar datos iniciales)."""
        with self._conexion.transaccion() as sesion:
            sesion.execute(delete(self.modelo))

    def _buscar(self, sesion: Session, *condiciones: Any) -> List[T]:
        consulta = select(self.modelo).where(*condiciones)
        consulta = consulta.order_by(self.modelo.id)
        return [self._a_entidad(r) for r in sesion.scalars(consulta)]

    def _buscar_uno(self, sesion: Session, *condiciones: Any) -> Optional[T]:
        registro = sesion.scalars(
            select(self.modelo).where(*condiciones).limit(1)).first()
        return None if registro is None else self._a_entidad(registro)


class RepositorioGenero(RepositorioSQL[Genero, GeneroModel]):
    """Persistencia de géneros literarios."""

    modelo = GeneroModel

    def _volcar(self, entidad: Genero, modelo: GeneroModel) -> None:
        modelo.nombre = entidad.nombre
        modelo.descripcion = entidad.descripcion

    def _a_entidad(self, modelo: GeneroModel) -> Genero:
        return Genero(modelo.nombre, modelo.descripcion, id=modelo.id)

    def leer_por_nombre(self, nombre: str) -> Optional[Genero]:
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(
                sesion,
                func.lower(GeneroModel.nombre) == nombre.strip().lower())


class RepositorioEditorial(RepositorioSQL[Editorial, EditorialModel]):
    """Persistencia de editoriales."""

    modelo = EditorialModel

    def _volcar(self, entidad: Editorial, modelo: EditorialModel) -> None:
        modelo.nombre = entidad.nombre
        modelo.pais = entidad.pais

    def _a_entidad(self, modelo: EditorialModel) -> Editorial:
        return Editorial(modelo.nombre, modelo.pais, id=modelo.id)

    def leer_por_nombre(self, nombre: str) -> Optional[Editorial]:
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(
                sesion,
                func.lower(EditorialModel.nombre) == nombre.strip().lower())


class RepositorioMoneda(RepositorioSQL[Moneda, MonedaModel]):
    """Persistencia de monedas."""

    modelo = MonedaModel

    def _volcar(self, entidad: Moneda, modelo: MonedaModel) -> None:
        modelo.codigo = entidad.codigo
        modelo.nombre = entidad.nombre
        modelo.simbolo = entidad.simbolo

    def _a_entidad(self, modelo: MonedaModel) -> Moneda:
        return Moneda(modelo.codigo, modelo.nombre, modelo.simbolo,
                      id=modelo.id)

    def leer_por_codigo(self, codigo: str) -> Optional[Moneda]:
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(
                sesion, MonedaModel.codigo == codigo.strip().upper())


class RepositorioTipoCotizacion(
        RepositorioSQL[TipoCotizacion, TipoCotizacionModel]):
    """Persistencia de tipos de cotización."""

    modelo = TipoCotizacionModel

    def _volcar(self, entidad: TipoCotizacion,
                modelo: TipoCotizacionModel) -> None:
        modelo.nombre = entidad.nombre
        modelo.descripcion = entidad.descripcion
        modelo.moneda_id = entidad.moneda_id

    def _a_entidad(self, modelo: TipoCotizacionModel) -> TipoCotizacion:
        return TipoCotizacion(modelo.nombre, modelo.descripcion,
                              modelo.moneda_id, id=modelo.id)

    def leer_por_nombre(self, nombre: str,
                        moneda_id: Optional[int] = None
                        ) -> Optional[TipoCotizacion]:
        """Busca por nombre (sin distinguir mayúsculas), opcionalmente
        acotado a una moneda."""
        condiciones: List[Any] = [
            func.lower(TipoCotizacionModel.nombre) == nombre.strip().lower()]
        if moneda_id is not None:
            condiciones.append(TipoCotizacionModel.moneda_id == moneda_id)
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(sesion, *condiciones)

    def leer_por_moneda(self, moneda_id: int) -> List[TipoCotizacion]:
        with self._conexion.transaccion() as sesion:
            return self._buscar(
                sesion, TipoCotizacionModel.moneda_id == moneda_id)


class RepositorioLibro(RepositorioSQL[Libro, LibroModel]):
    """Persistencia de libros."""

    modelo = LibroModel

    def _volcar(self, entidad: Libro, modelo: LibroModel) -> None:
        modelo.isbn = entidad.isbn
        modelo.titulo = entidad.titulo
        modelo.autor = entidad.autor
        modelo.editorial_id = entidad.editorial_id
        modelo.genero_id = entidad.genero_id
        modelo.anio = entidad.anio

    def _a_entidad(self, modelo: LibroModel) -> Libro:
        return Libro(modelo.isbn, modelo.titulo, modelo.autor,
                     modelo.editorial_id, modelo.genero_id, modelo.anio,
                     id=modelo.id)

    def leer_por_isbn(self, isbn: str) -> Optional[Libro]:
        isbn = isbn.replace("-", "").replace(" ", "")
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(sesion, LibroModel.isbn == isbn)

    def leer_por_genero(self, genero_id: int) -> List[Libro]:
        with self._conexion.transaccion() as sesion:
            return self._buscar(sesion, LibroModel.genero_id == genero_id)

    def leer_por_editorial(self, editorial_id: int) -> List[Libro]:
        with self._conexion.transaccion() as sesion:
            return self._buscar(sesion,
                                LibroModel.editorial_id == editorial_id)

    def buscar_por_titulo(self, texto: str) -> List[Libro]:
        patron = f"%{texto.strip().lower()}%"
        with self._conexion.transaccion() as sesion:
            return self._buscar(sesion,
                                func.lower(LibroModel.titulo).like(patron))


class RepositorioPrecio(RepositorioSQL[Precio, PrecioModel]):
    """Persistencia de precios."""

    modelo = PrecioModel

    def _volcar(self, entidad: Precio, modelo: PrecioModel) -> None:
        modelo.libro_id = entidad.libro_id
        modelo.moneda_id = entidad.moneda_id
        modelo.valor = entidad.valor

    def _a_entidad(self, modelo: PrecioModel) -> Precio:
        return Precio(modelo.libro_id, modelo.moneda_id, modelo.valor,
                      id=modelo.id)

    def leer_por_libro(self, libro_id: int) -> List[Precio]:
        with self._conexion.transaccion() as sesion:
            return self._buscar(sesion, PrecioModel.libro_id == libro_id)

    def leer_por_moneda(self, moneda_id: int) -> List[Precio]:
        with self._conexion.transaccion() as sesion:
            return self._buscar(sesion, PrecioModel.moneda_id == moneda_id)

    def leer_por_libro_y_moneda(self, libro_id: int,
                                moneda_id: int) -> Optional[Precio]:
        with self._conexion.transaccion() as sesion:
            return self._buscar_uno(sesion, PrecioModel.libro_id == libro_id,
                                    PrecioModel.moneda_id == moneda_id)

    def eliminar_por_libro(self, libro_id: int) -> int:
        """Elimina todos los precios de un libro y devuelve cuántos borró."""
        with self._conexion.transaccion() as sesion:
            resultado = sesion.execute(
                delete(PrecioModel).where(PrecioModel.libro_id == libro_id))
            return int(resultado.rowcount or 0)


# ---------------------------------------------------------------------------
# Repositorios con clave natural (sin id autoincremental)
# ---------------------------------------------------------------------------

class RepositorioStock(IRepositorioStock):
    """Persistencia de stock; la clave es el id del libro."""

    def __init__(self, conexion: ConexionDB) -> None:
        self._conexion = conexion

    @staticmethod
    def _a_entidad(modelo: StockModel) -> Stock:
        return Stock(modelo.libro_id, modelo.cantidad, modelo.cantidad_minima)

    def crear(self, stock: Stock) -> Stock:
        with self._conexion.transaccion() as sesion:
            if sesion.get(StockModel, stock.libro_id) is not None:
                raise ValueError(
                    f"Ya existe stock para el libro {stock.libro_id}.")
            sesion.add(StockModel(libro_id=stock.libro_id,
                                  cantidad=stock.cantidad,
                                  cantidad_minima=stock.cantidad_minima))
        return stock

    def leer_por_libro(self, libro_id: int) -> Optional[Stock]:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(StockModel, libro_id)
            return None if registro is None else self._a_entidad(registro)

    def leer_todos(self) -> List[Stock]:
        with self._conexion.transaccion() as sesion:
            consulta = select(StockModel).order_by(StockModel.libro_id)
            return [self._a_entidad(r) for r in sesion.scalars(consulta)]

    def actualizar(self, stock: Stock) -> Stock:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(StockModel, stock.libro_id)
            if registro is None:
                raise ValueError(
                    f"No existe stock para el libro {stock.libro_id}.")
            registro.cantidad = stock.cantidad
            registro.cantidad_minima = stock.cantidad_minima
        return stock

    def eliminar(self, libro_id: int) -> bool:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(StockModel, libro_id)
            if registro is None:
                return False
            sesion.delete(registro)
            return True

    def contar(self) -> int:
        with self._conexion.transaccion() as sesion:
            return int(sesion.execute(
                select(func.count()).select_from(StockModel)).scalar() or 0)

    def vaciar(self) -> None:
        with self._conexion.transaccion() as sesion:
            sesion.execute(delete(StockModel))


class RepositorioCotizacionDolar(IRepositorioCotizacionDolar):
    """Persistencia de cotizaciones; la clave es (tipo_id, fecha)."""

    def __init__(self, conexion: ConexionDB) -> None:
        self._conexion = conexion

    @staticmethod
    def _a_entidad(modelo: CotizacionModel) -> CotizacionDolar:
        return CotizacionDolar(modelo.tipo_id, modelo.fecha, modelo.compra,
                               modelo.venta)

    def crear(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        with self._conexion.transaccion() as sesion:
            clave = (cotizacion.tipo_id, cotizacion.fecha)
            if sesion.get(CotizacionModel, clave) is not None:
                raise ValueError(
                    f"Ya existe una cotización del tipo {cotizacion.tipo_id}"
                    f" para la fecha {cotizacion.fecha}.")
            sesion.add(CotizacionModel(tipo_id=cotizacion.tipo_id,
                                       fecha=cotizacion.fecha,
                                       compra=cotizacion.compra,
                                       venta=cotizacion.venta))
        return cotizacion

    def leer_por_tipo_y_fecha(
            self, tipo_id: int,
            fecha: datetime.date) -> Optional[CotizacionDolar]:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(CotizacionModel, (tipo_id, fecha))
            return None if registro is None else self._a_entidad(registro)

    def leer_historico_por_tipo(self, tipo_id: int) -> List[CotizacionDolar]:
        with self._conexion.transaccion() as sesion:
            consulta = (select(CotizacionModel)
                        .where(CotizacionModel.tipo_id == tipo_id)
                        .order_by(CotizacionModel.fecha))
            return [self._a_entidad(r) for r in sesion.scalars(consulta)]

    def leer_ultima_por_tipo(self, tipo_id: int) -> Optional[CotizacionDolar]:
        """Devuelve la cotización más reciente de un tipo, si existe."""
        with self._conexion.transaccion() as sesion:
            consulta = (select(CotizacionModel)
                        .where(CotizacionModel.tipo_id == tipo_id)
                        .order_by(CotizacionModel.fecha.desc()).limit(1))
            registro = sesion.scalars(consulta).first()
            return None if registro is None else self._a_entidad(registro)

    def leer_todos(self) -> List[CotizacionDolar]:
        with self._conexion.transaccion() as sesion:
            consulta = select(CotizacionModel).order_by(
                CotizacionModel.tipo_id, CotizacionModel.fecha)
            return [self._a_entidad(r) for r in sesion.scalars(consulta)]

    def actualizar(self, cotizacion: CotizacionDolar) -> CotizacionDolar:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(
                CotizacionModel, (cotizacion.tipo_id, cotizacion.fecha))
            if registro is None:
                raise ValueError(
                    f"No existe una cotización del tipo {cotizacion.tipo_id}"
                    f" para la fecha {cotizacion.fecha}.")
            registro.compra = cotizacion.compra
            registro.venta = cotizacion.venta
        return cotizacion

    def eliminar(self, tipo_id: int, fecha: datetime.date) -> bool:
        with self._conexion.transaccion() as sesion:
            registro = sesion.get(CotizacionModel, (tipo_id, fecha))
            if registro is None:
                return False
            sesion.delete(registro)
            return True

    def contar(self) -> int:
        with self._conexion.transaccion() as sesion:
            return int(sesion.execute(select(func.count()).select_from(
                CotizacionModel)).scalar() or 0)

    def vaciar(self) -> None:
        with self._conexion.transaccion() as sesion:
            sesion.execute(delete(CotizacionModel))


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
    def desde_conexion(cls, conexion: ConexionDB) -> "Repositorios":
        """Crea todos los repositorios sobre la misma conexión."""
        return cls(
            generos=RepositorioGenero(conexion),
            editoriales=RepositorioEditorial(conexion),
            monedas=RepositorioMoneda(conexion),
            tipos_cotizacion=RepositorioTipoCotizacion(conexion),
            libros=RepositorioLibro(conexion),
            precios=RepositorioPrecio(conexion),
            stock=RepositorioStock(conexion),
            cotizaciones=RepositorioCotizacionDolar(conexion),
        )

    def todos(self) -> List[Any]:
        """Lista de repositorios, en el orden de carga de datos."""
        return [self.generos, self.editoriales, self.monedas,
                self.tipos_cotizacion, self.libros, self.precios,
                self.stock, self.cotizaciones]

    def esta_vacia(self) -> bool:
        """Indica si ninguna tabla del sistema tiene registros."""
        return all(repositorio.contar() == 0 for repositorio in self.todos())

    def vaciar(self) -> None:
        """Borra los datos de todas las tablas (en orden inverso de carga)."""
        for repositorio in reversed(self.todos()):
            repositorio.vaciar()
