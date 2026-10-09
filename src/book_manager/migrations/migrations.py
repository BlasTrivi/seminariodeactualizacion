"""Migración de datos: de los archivos CSV del TP1 a la base de datos.

``migrar_datos`` lee cada archivo de ``migrations/csv``, lo convierte en
entidades (reutilizando ``desde_dict`` del Sprint 1), inserta los
registros en la base a través de los repositorios y, al mismo tiempo,
genera en ``migrations/sql`` un archivo ``.sql`` por tabla con las
sentencias ``INSERT`` equivalentes (más ``00_esquema.sql`` con el DDL de
las tablas). Así queda constancia de la carga inicial y puede repetirse
en cualquier motor compatible con SQL.
"""
from __future__ import annotations

import csv
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Type

from sqlalchemy import Date, Integer, Numeric
from sqlalchemy.schema import CreateTable

from book_manager.database.connection import ConexionDB
from book_manager.entities.entities import (
    CotizacionDolar, Editorial, Genero, Libro, Moneda, Precio, Serializable,
    Stock, TipoCotizacion,
)
from book_manager.models.models import (
    Base, CotizacionModel, EditorialModel, GeneroModel, LibroModel,
    MonedaModel, PrecioModel, StockModel, TipoCotizacionModel,
)
from book_manager.repositories.repositories import Repositorios

ARCHIVO_ESQUEMA = "00_esquema.sql"

#: (archivo csv, clase de entidad, modelo ORM, atributo de Repositorios)
#: en el orden que respeta las claves foráneas.
TABLAS: Sequence[Tuple[str, Type[Serializable], Type[Base], str]] = (
    ("generos.csv", Genero, GeneroModel, "generos"),
    ("editoriales.csv", Editorial, EditorialModel, "editoriales"),
    ("monedas.csv", Moneda, MonedaModel, "monedas"),
    ("tipos_cotizacion.csv", TipoCotizacion, TipoCotizacionModel,
     "tipos_cotizacion"),
    ("libros.csv", Libro, LibroModel, "libros"),
    ("precios.csv", Precio, PrecioModel, "precios"),
    ("stock.csv", Stock, StockModel, "stock"),
    ("cotizaciones_dolar.csv", CotizacionDolar, CotizacionModel,
     "cotizaciones"),
)


@dataclass
class ResultadoMigracion:
    """Resumen de la migración de una tabla."""

    tabla: str
    archivo_csv: Path
    archivo_sql: Path
    registros: int

    def __str__(self) -> str:
        return (f"{self.tabla:<18} {self.registros:>4} registros  "
                f"-> {self.archivo_sql.name}")


class GeneradorSQL:
    """Convierte entidades en sentencias ``INSERT`` según el modelo ORM."""

    def __init__(self, modelo: Type[Base]) -> None:
        self._tabla = modelo.__table__
        self._columnas = [columna.name for columna in self._tabla.columns]

    @property
    def nombre_tabla(self) -> str:
        return str(self._tabla.name)

    def _literal(self, columna: str, valor: object) -> str:
        """Representa un valor como literal SQL según el tipo de columna."""
        if valor is None or valor == "":
            tipo = self._tabla.columns[columna].type
            if isinstance(tipo, (Integer, Numeric, Date)):
                return "NULL"
            return "''"
        tipo = self._tabla.columns[columna].type
        if isinstance(tipo, Integer):
            return str(int(str(valor)))
        if isinstance(tipo, Numeric):
            return f"{float(str(valor)):.2f}"
        if isinstance(tipo, Date):
            fecha = valor if isinstance(valor, datetime.date) else str(valor)
            return f"'{fecha}'"
        texto = str(valor).replace("'", "''")
        return f"'{texto}'"

    def insert(self, entidad: Serializable) -> str:
        """Sentencia INSERT con todas las columnas de la entidad."""
        datos = entidad.a_dict()
        columnas = [c for c in self._columnas if c in datos]
        valores = ", ".join(self._literal(c, datos[c]) for c in columnas)
        return (f"INSERT INTO {self.nombre_tabla} ({', '.join(columnas)}) "
                f"VALUES ({valores});")

    def script(self, entidades: Sequence[Serializable],
               origen: str) -> str:
        """Script completo con encabezado y un INSERT por registro."""
        lineas = [
            f"-- Tabla: {self.nombre_tabla}",
            f"-- Origen: {origen}",
            f"-- Registros: {len(entidades)}",
            "-- Generado por book_manager/migrations/migrations.py",
            "",
        ]
        lineas.extend(self.insert(entidad) for entidad in entidades)
        return "\n".join(lineas) + "\n"


class MigradorCSV:
    """Orquesta la migración completa (lectura, inserción y scripts SQL)."""

    def __init__(self, conexion: ConexionDB, carpeta_csvs: Path,
                 carpeta_sqls: Path) -> None:
        self._conexion = conexion
        self._carpeta_csvs = Path(carpeta_csvs)
        self._carpeta_sqls = Path(carpeta_sqls)
        self._repos = Repositorios.desde_conexion(conexion)

    # -- lectura de CSV ---------------------------------------------------

    @staticmethod
    def leer_csv(ruta: Path,
                 clase: Type[Serializable]) -> List[Serializable]:
        """Lee un archivo CSV y devuelve las entidades que contiene."""
        if not ruta.exists():
            raise FileNotFoundError(f"No se encuentra el archivo {ruta}.")
        with ruta.open(newline="", encoding="utf-8") as archivo:
            return [clase.desde_dict(fila) for fila in csv.DictReader(archivo)]

    # -- scripts ----------------------------------------------------------

    def generar_esquema(self) -> Path:
        """Escribe ``00_esquema.sql`` con el CREATE TABLE de cada tabla."""
        self._carpeta_sqls.mkdir(parents=True, exist_ok=True)
        lineas = ["-- Esquema de Book Manager (Sprint 2)",
                  f"-- Dialecto: {self._conexion.dialecto}",
                  "-- Generado por book_manager/migrations/migrations.py", ""]
        for _, _, modelo, _ in TABLAS:
            ddl = CreateTable(modelo.__table__).compile(self._conexion.engine)
            lineas.extend(linea.rstrip() for linea in str(ddl).strip()
                          .splitlines())
            lineas[-1] += ";"
            lineas.append("")
        ruta = self._carpeta_sqls / ARCHIVO_ESQUEMA
        ruta.write_text("\n".join(lineas), encoding="utf-8")
        return ruta

    # -- migración --------------------------------------------------------

    def migrar(self, vaciar: bool = True) -> List[ResultadoMigracion]:
        """Ejecuta la migración de todas las tablas.

        Args:
            vaciar (bool): Si es True se borran los datos existentes antes
                de insertar, para que la migración sea repetible.

        Returns:
            List[ResultadoMigracion]: Un resumen por tabla migrada.
        """
        self._conexion.crear_tablas()
        self.generar_esquema()
        if vaciar:
            self._repos.vaciar()
        resultados: List[ResultadoMigracion] = []
        for orden, (archivo, clase, modelo, atributo) in enumerate(TABLAS, 1):
            ruta_csv = self._carpeta_csvs / archivo
            entidades = self.leer_csv(ruta_csv, clase)
            repositorio = getattr(self._repos, atributo)
            for entidad in entidades:
                repositorio.crear(entidad)
            generador = GeneradorSQL(modelo)
            ruta_sql = self._carpeta_sqls / \
                f"{orden:02d}_{generador.nombre_tabla}.sql"
            ruta_sql.write_text(generador.script(entidades, archivo),
                                encoding="utf-8")
            resultados.append(ResultadoMigracion(
                generador.nombre_tabla, ruta_csv, ruta_sql, len(entidades)))
        return resultados


def migrar_datos(carpeta_csvs: str, carpeta_sqls: str,
                 conexion: Optional[ConexionDB] = None
                 ) -> List[ResultadoMigracion]:
    """ Función encargada de la migración de datos de csv a sql.
    Se encarga de leer los archivos csv y crear los archivos sql
    para la inserción en la base de datos.

    Args:
        carpeta_csvs (str): Carpeta donde se encuentran los archivos csv
            de origen.
        carpeta_sqls (str): Carpeta donde se deben guardar los archivos
            sql generados.
        conexion (Optional[ConexionDB]): Conexión a usar; si no se indica
            se crea una con la configuración del ``.env``.

    Returns:
        List[ResultadoMigracion]: Resumen con la cantidad de registros
            migrados y el archivo ``.sql`` generado por cada tabla.
    """
    conexion = conexion or ConexionDB()
    migrador = MigradorCSV(conexion, Path(carpeta_csvs), Path(carpeta_sqls))
    return migrador.migrar()


def resumen(resultados: Sequence[ResultadoMigracion]) -> Dict[str, int]:
    """Diccionario ``tabla -> registros`` a partir de los resultados."""
    return {r.tabla: r.registros for r in resultados}
