"""Punto de entrada de Book Manager (Sprint 2).

Uso desde el notebook o desde Python::

    from book_manager.main import main
    main(import_default_data=False)

Uso desde la terminal (parado en ``src/``)::

    python -m book_manager.main

Secuencia de arranque:

1. Se abre la conexión (``ConexionDB``) con la URL del ``.env``.
2. Se crean las tablas si no existen.
3. Si se pide ``import_default_data`` se regeneran los CSV de origen; si
   la base está vacía (primera ejecución) se migran los CSV del TP1 a las
   tablas y se generan los archivos ``.sql``.
4. Se arman repositorios y servicios y se lanza la consola.
"""
from __future__ import annotations

from pathlib import Path

from book_manager.database.connection import ConexionDB
from book_manager.migrations.migrations import migrar_datos
from book_manager.preload_data.preload_data import (
    archivos_csv_existen, cargar_datos_iniciales,
)
from book_manager.repositories.repositories import Repositorios
from book_manager.services.services import Servicios
from book_manager.ui.console import ConsolaUI

CARPETA_MIGRACIONES = Path(__file__).resolve().parent / "migrations"
RUTA_CSV = CARPETA_MIGRACIONES / "csv"
RUTA_SQL = CARPETA_MIGRACIONES / "sql"


def preparar_base(conexion: ConexionDB,
                  import_default_data: bool = False) -> Repositorios:
    """Deja la base lista para usar y devuelve los repositorios.

    Args:
        conexion (ConexionDB): Conexión a la base de datos.
        import_default_data (bool): Si es True se regeneran los CSV con
            los datos iniciales y se vuelve a migrar todo a la base.

    Returns:
        Repositorios: Repositorios ya conectados a la base poblada.
    """
    conexion.crear_tablas()
    repositorios = Repositorios.desde_conexion(conexion)
    if import_default_data or not archivos_csv_existen(RUTA_CSV):
        cargar_datos_iniciales(RUTA_CSV)
        print(f"Archivos CSV de origen generados en {RUTA_CSV}")
    if import_default_data or repositorios.esta_vacia():
        resultados = migrar_datos(str(RUTA_CSV), str(RUTA_SQL), conexion)
        total = sum(r.registros for r in resultados)
        print(f"Migración CSV -> {conexion.dialecto}: {total} registros en "
              f"{len(resultados)} tablas; scripts SQL en {RUTA_SQL}")
    return repositorios


def main(import_default_data: bool = False) -> None:
    """Arma las capas del sistema y lanza la interfaz de consola.

    Args:
        import_default_data (bool): si es True se regeneran los datos
            iniciales (CSV y base de datos). Si es False se trabaja con
            los datos ya persistidos; si la base estuviera vacía se
            migran los CSV de todos modos.
    """
    conexion = ConexionDB()
    print(f"Base de datos: {conexion.url}")
    repositorios = preparar_base(conexion, import_default_data)
    servicios = Servicios.desde_repositorios(repositorios)
    try:
        ConsolaUI(servicios).ejecutar()
    finally:
        conexion.cerrar()


if __name__ == "__main__":
    main()
