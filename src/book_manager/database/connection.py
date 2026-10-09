"""Conexión a la base de datos con SQLAlchemy (Sprint 2).

Este módulo concentra todo lo relativo a la conexión:

- ``cargar_entorno``: lee el archivo ``.env`` de la raíz del proyecto para
  no escribir credenciales ni URLs en el código (conexión segura).
- ``Base``: clase declarativa de la que heredan los modelos (tablas).
- ``ConexionDB``: administra el motor (``Engine``) y la fábrica de
  sesiones; crea o elimina las tablas y prueba la conexión.
- ``Transaccion``: context manager que abre una sesión, confirma los
  cambios si el bloque termina bien y los revierte ante cualquier error.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType
from typing import Any, List, Optional, Type

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

#: Raíz del repositorio (carpeta que contiene ``src``, ``.env``, etc.).
RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
ARCHIVO_ENV = RAIZ_PROYECTO / ".env"

VARIABLE_URL = "DATABASE_URL"
URL_POR_DEFECTO = "sqlite:///book_manager.db"
PREFIJO_SQLITE = "sqlite:///"


def cargar_entorno(archivo: Path = ARCHIVO_ENV) -> bool:
    """Carga las variables del archivo ``.env`` en ``os.environ``.

    Args:
        archivo (Path): Ruta del archivo ``.env``. Por defecto el de la
            raíz del proyecto.

    Returns:
        bool: True si el archivo existía y se cargó alguna variable.
    """
    return load_dotenv(archivo, override=False)


def variable_entorno(nombre: str, por_defecto: Optional[str] = None) -> str:
    """Devuelve una variable de entorno (cargando antes el ``.env``).

    Args:
        nombre (str): Nombre de la variable (por ejemplo ``API_URL``).
        por_defecto (Optional[str]): Valor a usar si no está definida.

    Returns:
        str: El valor de la variable.

    Raises:
        ValueError: Si la variable no existe y no hay valor por defecto.
    """
    cargar_entorno()
    valor = os.environ.get(nombre, por_defecto)
    if valor is None or not str(valor).strip():
        raise ValueError(
            f"Falta la variable '{nombre}'. Definirla en {ARCHIVO_ENV}.")
    return str(valor).strip()


class Base(DeclarativeBase):
    """Clase base declarativa: todos los modelos (tablas) heredan de ella."""


# ---------------------------------------------------------------------------
# Ejercicio 02: clase ConexionDB
# ---------------------------------------------------------------------------

class ConexionDB:
    """Maneja la conexión a la base de datos mediante SQLAlchemy.

    La URL se toma del parámetro ``url`` o, si no se indica, de la
    variable ``DATABASE_URL`` del archivo ``.env``. Si tampoco existe se
    usa una base SQLite local (``book_manager.db`` en la raíz del
    proyecto). Para usar PostgreSQL/Supabase alcanza con cambiar la URL
    en el ``.env``; el resto del sistema no se modifica.
    """

    def __init__(self, url: Optional[str] = None, echo: bool = False) -> None:
        self._url: str = self._resolver_url(url)
        self._engine: Engine = create_engine(self._url, echo=echo)
        if self._engine.dialect.name == "sqlite":
            self._activar_claves_foraneas_sqlite(self._engine)
        self._fabrica_sesiones = sessionmaker(
            bind=self._engine, expire_on_commit=False)

    # -- propiedades ------------------------------------------------------

    @property
    def url(self) -> str:
        """URL de conexión con la contraseña ocultada."""
        return make_url(self._url).render_as_string(hide_password=True)

    @property
    def engine(self) -> Engine:
        """Motor de SQLAlchemy (se expone para inspección y DDL)."""
        return self._engine

    @property
    def dialecto(self) -> str:
        """Nombre del motor de base de datos (sqlite, postgresql, ...)."""
        return self._engine.dialect.name

    # -- resolución de la URL ---------------------------------------------

    @classmethod
    def _resolver_url(cls, url: Optional[str]) -> str:
        """Obtiene la URL desde el parámetro o del ``.env``.

        Las rutas relativas de SQLite se anclan a la raíz del proyecto para
        que el archivo quede siempre en el mismo lugar, sin importar desde
        qué carpeta se ejecute el sistema.
        """
        if url is None:
            url = variable_entorno(VARIABLE_URL, URL_POR_DEFECTO)
        if url.startswith(PREFIJO_SQLITE):
            ruta = url[len(PREFIJO_SQLITE):]
            if ruta and ruta != ":memory:" and not Path(ruta).is_absolute():
                url = f"{PREFIJO_SQLITE}{(RAIZ_PROYECTO / ruta).as_posix()}"
        return url

    @staticmethod
    def _activar_claves_foraneas_sqlite(engine: Engine) -> None:
        """SQLite no valida claves foráneas salvo que se active el PRAGMA."""

        @event.listens_for(engine, "connect")
        def _activar(conexion_dbapi: Any, _registro: Any) -> None:
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # -- operaciones ------------------------------------------------------

    def probar_conexion(self) -> bool:
        """Ejecuta ``SELECT 1`` para verificar que la base responde."""
        with self._engine.connect() as conexion:
            return conexion.execute(text("SELECT 1")).scalar() == 1

    def crear_tablas(self) -> None:
        """Crea todas las tablas definidas en los modelos (si no existen)."""
        # Importación local: registra los modelos en ``Base.metadata``
        # evitando una importación circular (models importa Base de acá).
        from book_manager.models import models  # noqa: F401
        Base.metadata.create_all(self._engine)

    def eliminar_tablas(self) -> None:
        """Elimina todas las tablas del sistema (usado en pruebas)."""
        from book_manager.models import models  # noqa: F401
        Base.metadata.drop_all(self._engine)

    def nombres_tablas(self) -> List[str]:
        """Devuelve los nombres de las tablas existentes en la base."""
        return sorted(inspect(self._engine).get_table_names())

    def nueva_sesion(self) -> Session:
        """Abre una sesión; quien la pide es responsable de cerrarla."""
        return self._fabrica_sesiones()

    def transaccion(self) -> "Transaccion":
        """Devuelve el context manager de transacciones (Ejercicio 03)."""
        return Transaccion(self._fabrica_sesiones)

    def cerrar(self) -> None:
        """Libera las conexiones del pool."""
        self._engine.dispose()

    def __repr__(self) -> str:
        return f"ConexionDB(url={self.url!r})"


# ---------------------------------------------------------------------------
# Ejercicio 03: context manager para las transacciones
# ---------------------------------------------------------------------------

class Transaccion:
    """Context manager que delimita una unidad de trabajo atómica.

    Uso::

        with conexion.transaccion() as sesion:
            sesion.add(modelo)
            ...  # al salir del bloque se hace commit

    Si dentro del bloque se lanza una excepción se ejecuta ``rollback`` y
    la excepción se propaga; en todos los casos la sesión se cierra.
    """

    def __init__(self, fabrica_sesiones: sessionmaker[Session]) -> None:
        self._fabrica = fabrica_sesiones
        self._sesion: Optional[Session] = None

    @property
    def sesion(self) -> Session:
        """Sesión activa; falla si se consulta fuera del bloque ``with``."""
        if self._sesion is None:
            raise RuntimeError("La transacción no está abierta.")
        return self._sesion

    def __enter__(self) -> Session:
        self._sesion = self._fabrica()
        return self._sesion

    def __exit__(self, tipo_excepcion: Optional[Type[BaseException]],
                 excepcion: Optional[BaseException],
                 traza: Optional[TracebackType]) -> bool:
        sesion = self.sesion
        try:
            if tipo_excepcion is None:
                sesion.commit()
            else:
                sesion.rollback()
        except Exception:
            sesion.rollback()
            raise
        finally:
            sesion.close()
            self._sesion = None
        return False  # nunca se silencia la excepción original
