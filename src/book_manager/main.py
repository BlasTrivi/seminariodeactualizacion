"""Punto de entrada de Book Manager.

Uso desde el notebook o desde Python::

    from book_manager.main import main
    main(import_default_data=False)

Uso desde la terminal (parado en ``src/``)::

    python -m book_manager.main
"""
from __future__ import annotations

from pathlib import Path

from book_manager.preload_data.preload_data import cargar_datos_iniciales
from book_manager.repositories.repositories import Repositorios
from book_manager.services.services import Servicios
from book_manager.ui.console import ConsolaUI

RUTA_CSV = Path(__file__).resolve().parent / "migrations" / "csv"


def main(import_default_data: bool = False) -> None:
    """Arma las capas del sistema y lanza la interfaz de consola.

    Args:
        import_default_data (bool): si es True se regeneran los archivos
            CSV con los datos iniciales de ``preload_data``. Si es False
            se trabaja con los datos ya persistidos; si faltara algún
            archivo, se cargan los datos iniciales de todos modos.
    """
    repositorios = Repositorios.desde_directorio(RUTA_CSV)
    if import_default_data or not repositorios.archivos_existen():
        cargar_datos_iniciales(repositorios)
        print(f"Datos iniciales cargados en {RUTA_CSV}")
    servicios = Servicios.desde_repositorios(repositorios)
    ConsolaUI(servicios).ejecutar()


if __name__ == "__main__":
    main()
