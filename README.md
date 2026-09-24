# Book Manager

**Sprint actual: Sprint 1**

Trabajo Práctico Integrador - Grupo 15

- Blas Trivisonno

Repositorio: https://github.com/BlasTrivi/seminariodeactualizacion

## Objetivo

Aplicar los conocimientos adquiridos en programación orientada a objetos y
almacenamiento de datos en archivos para su persistencia, construyendo una
aplicación de consola (CLI) en Python que gestione el inventario de una
librería con venta al público.

## Introducción y contexto del Sprint 1

Una librería necesita modernizar su sistema de gestión de inventario de
libros. Debido a la fluctuación en los costos de importación de material
bibliográfico, el sistema debe manejar precios en distintas monedas y seguir
de cerca la cotización del dólar para valuar el catálogo según el tipo de
cambio elegido (Oficial, Blue, MEP, CCL, Tarjeta, etc.).

En este sprint se construye la base del sistema tomando como referencia el
sitio [Cúspide](https://www.cuspide.com/):

- Entidades del dominio con encapsulamiento: `Libro`, `Genero`, `Editorial`,
  `Moneda`, `TipoCotizacion`, `Precio`, `Stock` y `CotizacionDolar`.
- Repositorios con CRUD completo (Alta, Lectura, Modificación y Borrado)
  persistidos en archivos CSV.
- Servicios con la lógica de negocio (unicidad, integridad referencial,
  borrados en cascada o bloqueados) y reportes de valuación en tiempo real
  según la cotización del dólar.
- Datos iniciales (mínimo 10 registros por entidad) y una interfaz de
  consola con menús para operar cada CRUD y los reportes.

## Estructura del proyecto

```
book_manager/
├── src/
│   └── book_manager/
│       ├── entities/entities.py         # Entidades (Ejercicio 02)
│       ├── repositories/repositories.py # Persistencia CSV (Ejercicio 03)
│       ├── services/services.py         # Lógica de negocio (Ejercicio 04)
│       ├── preload_data/preload_data.py # Datos iniciales (Punto 05)
│       ├── migrations/csv/              # Archivos CSV generados
│       ├── ui/console.py                # Interfaz de consola (Punto 06)
│       └── main.py                      # Punto de entrada (Punto 07)
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

## Cómo ejecutar

El proyecto usa únicamente la biblioteca estándar de Python (3.10 o
superior); no requiere instalar dependencias.

Desde la terminal, parado en `src/`:

```bash
cd src
python -m book_manager.main
```

Desde un notebook (Google Colab):

```python
from book_manager.main import main
main(import_default_data=False)   # True regenera los datos iniciales
```

Si falta algún archivo CSV, el sistema carga los datos iniciales de forma
automática.

## Reportes disponibles

1. Catálogo valuado según el tipo de dólar elegido (precio en ARS y USD).
2. Cotización de un libro puntual.
3. Libros con stock por debajo del mínimo.
4. Valor total del inventario en ARS y USD.
5. Histórico de cotizaciones por tipo, con la variación del período.
