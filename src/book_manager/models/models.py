"""Modelos ORM: tablas del sistema con sus tipos de datos y relaciones.

Cada clase ``*Model`` describe una tabla de la base de datos relacional.
Las entidades del dominio (``entities.py``) siguen siendo las que usan los
servicios y la interfaz; los repositorios se encargan de convertir
entidad <-> modelo. De esta forma la lógica de negocio no depende del
motor de base de datos.

Esquema (normalizado):

    generos(id, nombre, descripcion)
    editoriales(id, nombre, pais)
    monedas(id, codigo, nombre, simbolo)
    tipos_cotizacion(id, nombre, descripcion, moneda_id -> monedas)
    libros(id, isbn, titulo, autor, editorial_id -> editoriales,
           genero_id -> generos, anio)
    precios(id, libro_id -> libros, moneda_id -> monedas, valor)
    stock(libro_id -> libros [PK], cantidad, cantidad_minima)
    cotizaciones(tipo_id -> tipos_cotizacion [PK], fecha [PK],
                 compra, venta)
    precios_web(id, libro_id -> libros, fecha_extraccion, posicion,
                titulo, url, precio, precio_usd, url_imagen, formas_pago,
                descripcion, isbn, coincidencia, seleccionado)   [Sprint 3]
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from book_manager.database.connection import Base

#: Importes con dos decimales. ``asdecimal=False`` devuelve ``float`` para
#: mantener compatibilidad con las entidades del Sprint 1.
IMPORTE = Numeric(14, 2, asdecimal=False)


class GeneroModel(Base):
    """Tabla ``generos``: categoría literaria de un libro."""

    __tablename__ = "generos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False,
                                        unique=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False,
                                             default="")

    libros: Mapped[List["LibroModel"]] = relationship(back_populates="genero")


class EditorialModel(Base):
    """Tabla ``editoriales``: proveedor o distribuidora de los libros."""

    __tablename__ = "editoriales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False,
                                        unique=True)
    pais: Mapped[str] = mapped_column(String(60), nullable=False, default="")

    libros: Mapped[List["LibroModel"]] = relationship(
        back_populates="editorial")


class MonedaModel(Base):
    """Tabla ``monedas``: monedas en las que se expresa un precio."""

    __tablename__ = "monedas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(3), nullable=False,
                                        unique=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    simbolo: Mapped[str] = mapped_column(String(10), nullable=False,
                                         default="")

    precios: Mapped[List["PrecioModel"]] = relationship(
        back_populates="moneda")
    tipos_cotizacion: Mapped[List["TipoCotizacionModel"]] = relationship(
        back_populates="moneda")


class TipoCotizacionModel(Base):
    """Tabla ``tipos_cotizacion``: tipo de cambio de una moneda.

    Para el dólar existen varios tipos (Oficial, Blue, MEP, CCL...); para
    el resto de las monedas que publica la API hay un único tipo
    (Oficial). El nombre es único dentro de cada moneda.
    """

    __tablename__ = "tipos_cotizacion"
    __table_args__ = (
        UniqueConstraint("moneda_id", "nombre",
                         name="uq_tipo_cotizacion_moneda_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False,
                                             default="")
    moneda_id: Mapped[int] = mapped_column(
        ForeignKey("monedas.id"), nullable=False)

    moneda: Mapped["MonedaModel"] = relationship(
        back_populates="tipos_cotizacion")
    cotizaciones: Mapped[List["CotizacionModel"]] = relationship(
        back_populates="tipo", cascade="all, delete-orphan")


class LibroModel(Base):
    """Tabla ``libros``: títulos del catálogo."""

    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isbn: Mapped[str] = mapped_column(String(13), nullable=False,
                                      unique=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    autor: Mapped[str] = mapped_column(String(120), nullable=False)
    editorial_id: Mapped[int] = mapped_column(
        ForeignKey("editoriales.id"), nullable=False)
    genero_id: Mapped[int] = mapped_column(
        ForeignKey("generos.id"), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)

    editorial: Mapped["EditorialModel"] = relationship(
        back_populates="libros")
    genero: Mapped["GeneroModel"] = relationship(back_populates="libros")
    # Al borrar un libro se borran sus precios y su stock (cascada).
    precios: Mapped[List["PrecioModel"]] = relationship(
        back_populates="libro", cascade="all, delete-orphan")
    stock: Mapped[Optional["StockModel"]] = relationship(
        back_populates="libro", cascade="all, delete-orphan", uselist=False)
    precios_web: Mapped[List["PrecioWebModel"]] = relationship(
        back_populates="libro", cascade="all, delete-orphan")


class PrecioModel(Base):
    """Tabla ``precios``: valor de un libro en una moneda (único por par)."""

    __tablename__ = "precios"
    __table_args__ = (
        UniqueConstraint("libro_id", "moneda_id",
                         name="uq_precio_libro_moneda"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id", ondelete="CASCADE"), nullable=False)
    moneda_id: Mapped[int] = mapped_column(
        ForeignKey("monedas.id"), nullable=False)
    valor: Mapped[float] = mapped_column(IMPORTE, nullable=False)

    libro: Mapped["LibroModel"] = relationship(back_populates="precios")
    moneda: Mapped["MonedaModel"] = relationship(back_populates="precios")


class StockModel(Base):
    """Tabla ``stock``: cantidad disponible por libro (clave: libro)."""

    __tablename__ = "stock"

    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id", ondelete="CASCADE"), primary_key=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_minima: Mapped[int] = mapped_column(Integer, nullable=False,
                                                 default=0)

    libro: Mapped["LibroModel"] = relationship(back_populates="stock")


class CotizacionModel(Base):
    """Tabla ``cotizaciones``: histórico por tipo y fecha (clave compuesta)."""

    __tablename__ = "cotizaciones"

    tipo_id: Mapped[int] = mapped_column(
        ForeignKey("tipos_cotizacion.id", ondelete="CASCADE"),
        primary_key=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    compra: Mapped[float] = mapped_column(IMPORTE, nullable=False)
    venta: Mapped[float] = mapped_column(IMPORTE, nullable=False)

    tipo: Mapped["TipoCotizacionModel"] = relationship(
        back_populates="cotizaciones")


#: Nombre usado en el enunciado del Sprint 3 para la tabla de cotizaciones.
CotizacionDolarModel = CotizacionModel


class PrecioWebModel(Base):
    """Tabla ``precios_web``: resultados del scraper en Cúspide (Sprint 3).

    Cada ejecución del scraper guarda, por libro del catálogo, hasta 10
    resultados de la búsqueda; ``seleccionado`` marca el que se usa para
    comparar contra el precio interno.
    """

    __tablename__ = "precios_web"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id", ondelete="CASCADE"), nullable=False,
        index=True)
    fecha_extraccion: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    posicion: Mapped[int] = mapped_column(Integer, nullable=False)
    titulo: Mapped[str] = mapped_column(String(250), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    precio: Mapped[float] = mapped_column(IMPORTE, nullable=False)
    precio_usd: Mapped[Optional[float]] = mapped_column(IMPORTE,
                                                        nullable=True)
    url_imagen: Mapped[str] = mapped_column(String(500), nullable=False,
                                            default="")
    formas_pago: Mapped[str] = mapped_column(Text, nullable=False,
                                             default="")
    descripcion: Mapped[str] = mapped_column(Text, nullable=False,
                                             default="")
    isbn: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    coincidencia: Mapped[int] = mapped_column(Integer, nullable=False,
                                              default=0)
    seleccionado: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                               default=False)

    libro: Mapped["LibroModel"] = relationship(back_populates="precios_web")


#: Modelos en el orden que respeta las claves foráneas (para insertar).
MODELOS_EN_ORDEN = (
    GeneroModel, EditorialModel, MonedaModel, TipoCotizacionModel,
    LibroModel, PrecioModel, StockModel, CotizacionModel,
)
