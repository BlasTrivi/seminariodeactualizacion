"""Datos iniciales del sistema y su carga en ``migrations/csv``.

Cada lista contiene al menos 10 registros. La función
``cargar_datos_iniciales`` vacía los archivos CSV y vuelve a crear cada
registro a través de los repositorios, de modo que los archivos quedan
generados con el mismo código que usa el sistema en producción.
"""
from __future__ import annotations

import datetime
from typing import List

from book_manager.entities.entities import (
    CotizacionDolar, Editorial, Genero, Libro, Moneda, Precio, Stock,
    TipoCotizacion,
)
from book_manager.repositories.repositories import Repositorios

# Ids de referencia para armar las relaciones entre entidades.
ARS = 1
USD = 2


def generos() -> List[Genero]:
    return [
        Genero("Novela", "Narrativa de ficción extensa", id=1),
        Genero("Cuento", "Relatos breves de ficción", id=2),
        Genero("Ensayo", "Textos de reflexión y análisis", id=3),
        Genero("Infantil", "Libros para niños", id=4),
        Genero("Juvenil", "Libros para adolescentes", id=5),
        Genero("Técnico", "Programación, ingeniería y tecnología", id=6),
        Genero("Ciencia", "Divulgación científica", id=7),
        Genero("Historia", "Historia argentina y universal", id=8),
        Genero("Poesía", "Obras en verso", id=9),
        Genero("Autoayuda", "Desarrollo personal", id=10),
        Genero("Historieta", "Cómics y novela gráfica", id=11),
        Genero("Biografía", "Vidas de personajes destacados", id=12),
    ]


def editoriales() -> List[Editorial]:
    return [
        Editorial("Sudamericana", "Argentina", id=1),
        Editorial("Alfaguara", "España", id=2),
        Editorial("Emecé", "Argentina", id=3),
        Editorial("Debolsillo", "España", id=4),
        Editorial("Debate", "España", id=5),
        Editorial("Salamandra", "España", id=6),
        Editorial("No Starch Press", "Estados Unidos", id=7),
        Editorial("Prentice Hall", "Estados Unidos", id=8),
        Editorial("Seix Barral", "España", id=9),
        Editorial("Ediciones de la Flor", "Argentina", id=10),
        Editorial("Planeta", "España", id=11),
        Editorial("Crítica", "España", id=12),
    ]


def monedas() -> List[Moneda]:
    return [
        Moneda("ARS", "Peso argentino", "$", id=ARS),
        Moneda("USD", "Dólar estadounidense", "US$", id=USD),
        Moneda("EUR", "Euro", "€", id=3),
        Moneda("BRL", "Real brasileño", "R$", id=4),
        Moneda("CLP", "Peso chileno", "CLP$", id=5),
        Moneda("UYU", "Peso uruguayo", "$U", id=6),
        Moneda("MXN", "Peso mexicano", "MX$", id=7),
        Moneda("GBP", "Libra esterlina", "£", id=8),
        Moneda("JPY", "Yen japonés", "¥", id=9),
        Moneda("COP", "Peso colombiano", "COL$", id=10),
        Moneda("PEN", "Sol peruano", "S/", id=11),
        Moneda("CNY", "Yuan chino", "CN¥", id=12),
    ]


def tipos_cotizacion() -> List[TipoCotizacion]:
    return [
        TipoCotizacion("Oficial", "Cotización del Banco Nación", id=1),
        TipoCotizacion("Blue", "Mercado informal", id=2),
        TipoCotizacion("MEP", "Dólar Bolsa (mercado electrónico de pagos)",
                       id=3),
        TipoCotizacion("CCL", "Contado con liquidación", id=4),
        TipoCotizacion("Tarjeta", "Consumos en el exterior con tarjeta",
                       id=5),
        TipoCotizacion("Mayorista", "Mercado mayorista (BCRA)", id=6),
        TipoCotizacion("Cripto", "Cotización en exchanges de criptomonedas",
                       id=7),
        TipoCotizacion("Ahorro", "Dólar ahorro / solidario", id=8),
        TipoCotizacion("Turista", "Gastos de turismo en el exterior", id=9),
        TipoCotizacion("Exportación", "Liquidación de exportaciones", id=10),
        TipoCotizacion("Qatar", "Consumos con tarjeta sobre el tope "
                       "(histórico)", id=11),
        TipoCotizacion("Futuro", "Contratos de dólar futuro", id=12),
    ]


def libros() -> List[Libro]:
    return [
        Libro("9788497592208", "Cien años de soledad",
              "Gabriel García Márquez", editorial_id=4, genero_id=1,
              anio=1967, id=1),
        Libro("9788420437484", "Rayuela", "Julio Cortázar",
              editorial_id=2, genero_id=1, anio=1963, id=2),
        Libro("9789500427999", "El Aleph", "Jorge Luis Borges",
              editorial_id=3, genero_id=2, anio=1949, id=3),
        Libro("9788499089508", "Ficciones", "Jorge Luis Borges",
              editorial_id=4, genero_id=2, anio=1944, id=4),
        Libro("9788499926223", "Sapiens: De animales a dioses",
              "Yuval Noah Harari", editorial_id=5, genero_id=3, anio=2011,
              id=5),
        Libro("9788478887194", "El principito",
              "Antoine de Saint-Exupéry", editorial_id=6, genero_id=4,
              anio=1943, id=6),
        Libro("9781593279288", "Python Crash Course", "Eric Matthes",
              editorial_id=7, genero_id=6, anio=2019, id=7),
        Libro("9780132350884", "Clean Code", "Robert C. Martin",
              editorial_id=8, genero_id=6, anio=2008, id=8),
        Libro("9788478884452", "Harry Potter y la piedra filosofal",
              "J. K. Rowling", editorial_id=6, genero_id=5, anio=1997,
              id=9),
        Libro("9788499890944", "1984", "George Orwell",
              editorial_id=4, genero_id=1, anio=1949, id=10),
        Libro("9788498921182", "Breve historia del tiempo",
              "Stephen Hawking", editorial_id=12, genero_id=7, anio=1988,
              id=11),
        Libro("9789507315114", "El túnel", "Ernesto Sabato",
              editorial_id=9, genero_id=1, anio=1948, id=12),
        Libro("9789505157006", "Mafalda 1", "Quino",
              editorial_id=10, genero_id=11, anio=1970, id=13),
        Libro("9788499923048", "Steve Jobs", "Walter Isaacson",
              editorial_id=5, genero_id=12, anio=2011, id=14),
    ]


def precios() -> List[Precio]:
    return [
        Precio(libro_id=1, moneda_id=ARS, valor=24900.00, id=1),
        Precio(libro_id=2, moneda_id=ARS, valor=29900.00, id=2),
        Precio(libro_id=3, moneda_id=ARS, valor=21500.00, id=3),
        Precio(libro_id=4, moneda_id=ARS, valor=19900.00, id=4),
        Precio(libro_id=5, moneda_id=ARS, valor=32900.00, id=5),
        Precio(libro_id=6, moneda_id=ARS, valor=15900.00, id=6),
        Precio(libro_id=7, moneda_id=USD, valor=45.99, id=7),
        Precio(libro_id=8, moneda_id=USD, valor=52.50, id=8),
        Precio(libro_id=9, moneda_id=ARS, valor=27500.00, id=9),
        Precio(libro_id=10, moneda_id=ARS, valor=18900.00, id=10),
        Precio(libro_id=11, moneda_id=USD, valor=19.90, id=11),
        Precio(libro_id=12, moneda_id=ARS, valor=17900.00, id=12),
        Precio(libro_id=13, moneda_id=ARS, valor=14500.00, id=13),
        Precio(libro_id=14, moneda_id=USD, valor=24.99, id=14),
        Precio(libro_id=1, moneda_id=USD, valor=18.50, id=15),
        Precio(libro_id=5, moneda_id=USD, valor=22.00, id=16),
    ]


def stock() -> List[Stock]:
    return [
        Stock(libro_id=1, cantidad=12, cantidad_minima=5),
        Stock(libro_id=2, cantidad=7, cantidad_minima=3),
        Stock(libro_id=3, cantidad=9, cantidad_minima=3),
        Stock(libro_id=4, cantidad=15, cantidad_minima=5),
        Stock(libro_id=5, cantidad=4, cantidad_minima=5),
        Stock(libro_id=6, cantidad=25, cantidad_minima=10),
        Stock(libro_id=7, cantidad=3, cantidad_minima=2),
        Stock(libro_id=8, cantidad=2, cantidad_minima=3),
        Stock(libro_id=9, cantidad=18, cantidad_minima=6),
        Stock(libro_id=10, cantidad=11, cantidad_minima=4),
        Stock(libro_id=11, cantidad=6, cantidad_minima=2),
        Stock(libro_id=12, cantidad=0, cantidad_minima=2),
        Stock(libro_id=13, cantidad=1, cantidad_minima=5),
        Stock(libro_id=14, cantidad=5, cantidad_minima=2),
    ]


def cotizaciones() -> List[CotizacionDolar]:
    """Tres jornadas de cotización para los cinco tipos principales."""
    fechas = (datetime.date(2026, 9, 17), datetime.date(2026, 9, 18),
              datetime.date(2026, 9, 21))
    # tipo_id -> (compra, venta) por jornada
    valores = {
        1: ((1440.00, 1480.00), (1445.00, 1485.00), (1450.00, 1490.00)),
        2: ((1470.00, 1490.00), (1475.00, 1495.00), (1480.00, 1500.00)),
        3: ((1462.00, 1466.00), (1468.00, 1472.00), (1473.00, 1477.00)),
        4: ((1478.00, 1483.00), (1484.00, 1489.00), (1490.00, 1495.00)),
        5: ((1872.00, 1924.00), (1878.00, 1930.00), (1885.00, 1937.00)),
    }
    return [
        CotizacionDolar(tipo_id, fecha, compra, venta)
        for tipo_id, jornadas in valores.items()
        for fecha, (compra, venta) in zip(fechas, jornadas)
    ]


def cargar_datos_iniciales(repos: Repositorios) -> None:
    """Regenera los archivos CSV con los datos iniciales.

    Se vacían los repositorios y se crea cada registro mediante ``crear``,
    en el orden que respeta las relaciones (primero catálogos, luego
    libros y por último precios, stock y cotizaciones).
    """
    for repositorio in repos.todos():
        repositorio.vaciar()
    for genero in generos():
        repos.generos.crear(genero)
    for editorial in editoriales():
        repos.editoriales.crear(editorial)
    for moneda in monedas():
        repos.monedas.crear(moneda)
    for tipo in tipos_cotizacion():
        repos.tipos_cotizacion.crear(tipo)
    for libro in libros():
        repos.libros.crear(libro)
    for precio in precios():
        repos.precios.crear(precio)
    for registro in stock():
        repos.stock.crear(registro)
    for cotizacion in cotizaciones():
        repos.cotizaciones.crear(cotizacion)
