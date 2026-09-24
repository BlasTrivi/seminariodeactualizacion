"""Servicios: lógica de negocio aplicada sobre cada operación del CRUD.

Los servicios reciben los repositorios por inyección de dependencias y se
encargan de las validaciones que no pertenecen a una sola entidad:
unicidad (nombres, códigos, ISBN), integridad referencial (que exista el
género, la editorial, la moneda, el libro...), borrados bloqueados o en
cascada y los reportes que combinan varias entidades.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

from book_manager.entities.entities import (
    CotizacionDolar, Editorial, EntidadBase, Genero, Libro, Moneda, Precio,
    Stock, TipoCotizacion,
)
from book_manager.repositories.repositories import (
    IRepositorio, RepositorioCotizacionDolar, RepositorioEditorial,
    RepositorioGenero, RepositorioLibro, RepositorioMoneda,
    RepositorioPrecio, RepositorioStock, RepositorioTipoCotizacion,
    Repositorios,
)

T = TypeVar("T", bound=EntidadBase)

CODIGO_PESO = "ARS"
CODIGO_DOLAR = "USD"


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
                 repo_precios: RepositorioPrecio) -> None:
        super().__init__(repositorio)
        self._repo_monedas = repositorio
        self._repo_precios = repo_precios

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


class ServicioTipoCotizacion(ServicioBase[TipoCotizacion]):
    """Reglas de negocio para tipos de cotización."""

    nombre_entidad = "un tipo de cotización"

    def __init__(self, repositorio: RepositorioTipoCotizacion,
                 repo_cotizaciones: RepositorioCotizacionDolar) -> None:
        super().__init__(repositorio)
        self._repo_cotizaciones = repo_cotizaciones

    def _validar(self, entidad: TipoCotizacion) -> None:
        self._validar_nombre_unico(entidad, entidad.nombre)

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
        """Elimina el libro y, en cascada, sus precios y su stock."""
        eliminado = super().eliminar(id)
        if eliminado:
            self._repo_precios.eliminar_por_libro(id)
            self._repo_stock.eliminar(id)
        return eliminado


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


class ServicioCotizacionDolar:
    """Reglas de negocio para cotizaciones (clave: tipo y fecha)."""

    def __init__(self, repositorio: RepositorioCotizacionDolar,
                 repo_tipos: RepositorioTipoCotizacion) -> None:
        self._repositorio = repositorio
        self._repo_tipos = repo_tipos

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


# ---------------------------------------------------------------------------
# Reportes: valuación del catálogo según la cotización del dólar
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


class ServicioCotizador:
    """Convierte los precios de los libros entre pesos y dólares."""

    def __init__(self, libros: ServicioLibro, precios: ServicioPrecio,
                 monedas: ServicioMoneda, stock: ServicioStock,
                 cotizaciones: ServicioCotizacionDolar) -> None:
        self._libros = libros
        self._precios = precios
        self._monedas = monedas
        self._stock = stock
        self._cotizaciones = cotizaciones

    def cotizar_libro(self, libro_id: int, tipo_id: int) -> LibroCotizado:
        """Valúa un libro en ARS y USD usando la última cotización del tipo.

        Se toma el precio en USD si existe; en caso contrario el precio en
        ARS. Cualquier otra moneda no puede cotizarse en este sprint.
        """
        libro = self._libros.obtener(libro_id)
        cotizacion = self._cotizaciones.obtener_ultima(tipo_id)
        return self._cotizar(libro, cotizacion)

    def catalogo_valuado(self, tipo_id: int) -> List[LibroCotizado]:
        """Cotiza todos los libros que tengan precio en ARS o USD."""
        cotizacion = self._cotizaciones.obtener_ultima(tipo_id)
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

    @classmethod
    def desde_repositorios(cls, repos: Repositorios) -> "Servicios":
        """Construye todos los servicios inyectando los repositorios."""
        libros = ServicioLibro(repos.libros, repos.generos,
                               repos.editoriales, repos.precios, repos.stock)
        precios = ServicioPrecio(repos.precios, repos.libros, repos.monedas)
        monedas = ServicioMoneda(repos.monedas, repos.precios)
        stock = ServicioStock(repos.stock, repos.libros)
        cotizaciones = ServicioCotizacionDolar(repos.cotizaciones,
                                               repos.tipos_cotizacion)
        return cls(
            generos=ServicioGenero(repos.generos, repos.libros),
            editoriales=ServicioEditorial(repos.editoriales, repos.libros),
            monedas=monedas,
            tipos_cotizacion=ServicioTipoCotizacion(repos.tipos_cotizacion,
                                                    repos.cotizaciones),
            libros=libros,
            precios=precios,
            stock=stock,
            cotizaciones=cotizaciones,
            cotizador=ServicioCotizador(libros, precios, monedas, stock,
                                        cotizaciones),
        )
