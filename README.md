# Book Manager

**Sprint actual: Sprint 3**

Trabajo Práctico Integrador - Grupo 15

- Blas Trivisonno

Repositorio: https://github.com/BlasTrivi/seminariodeactualizacion

## Objetivo

Aplicar los conocimientos adquiridos en programación orientada a objetos y
almacenamiento de datos para su persistencia, construyendo una aplicación
de consola (CLI) en Python que gestione el inventario de una librería con
venta al público. En este sprint se incorpora la obtención de datos desde
la web (*web scraping*) para comparar nuestros precios con los de la
competencia.

## Introducción y contexto del Sprint 3

En la primera entrega el sistema guardaba cada entidad en archivos CSV y en
la segunda pasó a persistir en una base de datos relacional (SQLAlchemy),
con consultas a la API del dólar. En esta tercera entrega vamos a
**descargar y obtener datos de la web para trabajar con ellos**: la idea es
conocer los precios de nuestros competidores (librerías con venta online)
para compararnos con ellos y competir de forma más informada.

- La base de datos puede cargarse directamente desde los scripts `.sql`
  generados en la migración del Sprint 2.
- Un scraper hecho con **Scrapy** (`CuspideSpider`) busca en
  [Cúspide](https://cuspide.com) cada libro **de nuestro catálogo** (por
  título, solo los 10 primeros resultados) y obtiene el precio, la URL de
  la imagen, las formas de pago con su precio y la descripción detallada.
  Se usan *Item Loaders* para limpiar los datos y *Pipelines* para
  validarlos, calcular la coincidencia con nuestro libro y guardarlos.
- Antes de cada ejecución el usuario indica la diferencia de precios (%)
  a partir de la cual se genera una alerta; cada corrida deja un archivo
  CSV de alertas que se puede descargar.
- Se genera un reporte Excel con libro, precio interno, precio web,
  diferencia y fecha de extracción.
- Todas las operaciones del sistema quedan registradas en una tabla de
  **auditoría** mediante un decorador.

Se parte del último push de la rama `Sprint_2` y se trabaja sobre la rama
`Sprint_3`.

## Estructura del proyecto

```
book_manager/
├── src/
│   └── book_manager/
│       ├── database/connection.py        # ConexionDB + Transaccion
│       ├── entities/entities.py          # Entidades del dominio
│       ├── models/models.py              # Tablas ORM con relaciones
│       ├── preload_data/preload_data.py  # Datos iniciales -> CSV de origen
│       ├── repositories/repositories.py  # CRUD sobre base de datos
│       ├── scraper/                      # Proyecto Scrapy (Ej. 03)
│       │   ├── scrapy.cfg
│       │   ├── items.py · loaders.py · pipelines.py · settings.py
│       │   ├── runner.py                 # Ejecuta el spider en un proceso
│       │   └── spiders/cuspide.py        # CuspideSpider
│       ├── services/services.py          # Lógica de negocio, alertas,
│       │                                 # reportes y auditoría
│       ├── migrations/
│       │   ├── migrations.py             # CSV -> DB, .sql y carga desde .sql
│       │   ├── csv/                      # Archivos de origen (TP1)
│       │   └── sql/                      # Scripts generados en la migración
│       ├── reportes/                     # Alertas CSV y reportes Excel
│       ├── ui/console.py                 # Interfaz de consola
│       └── main.py                       # Punto de entrada
├── .env                                  # API_URL, DATABASE_URL, CUSPIDE_URL
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

## Cómo ejecutar

```bash
pip install -r requirements.txt
cd src
python -m book_manager.main
```

Desde un notebook (Google Colab):

```python
from book_manager.main import main
main(import_default_data=False)   # True regenera los CSV y vuelve a migrar
```
