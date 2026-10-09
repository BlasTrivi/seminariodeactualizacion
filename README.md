# Book Manager

**Sprint actual: Sprint 2**

Trabajo Práctico Integrador - Grupo 15

- Blas Trivisonno

Repositorio: https://github.com/BlasTrivi/seminariodeactualizacion

## Objetivo

Aplicar los conocimientos adquiridos en programación orientada a objetos y
almacenamiento de datos para su persistencia, construyendo una aplicación
de consola (CLI) en Python que gestione el inventario de una librería con
venta al público. En este sprint la persistencia pasa de archivos a una
base de datos relacional y se incorporan consultas a una API externa.

## Introducción y contexto del Sprint 2

En la primera entrega el sistema guardaba cada entidad en archivos CSV. En
esta segunda entrega se amplía el alcance haciendo que la aplicación
persista en una **base de datos relacional** mediante el ORM
[SQLAlchemy](https://www.sqlalchemy.org/):

- Se migran todos los datos cargados en los CSV del TP1 a tablas
  relacionales normalizadas, dejando constancia en archivos `.sql`.
- La conexión se configura de forma segura desde un archivo `.env`
  (`DATABASE_URL`), sin credenciales en el código. Por defecto se usa una
  base SQLite local; cambiando la URL se puede apuntar a PostgreSQL /
  Supabase sin tocar el resto del sistema.
- Las transacciones se manejan con un *context manager* que confirma los
  cambios al salir del bloque y los revierte ante cualquier error.
- Se consulta la API pública del dólar (https://dolarapi.com) para
  descargar y registrar las cotizaciones del día, y se suman reportes
  bimonetarios (pesos y otra moneda) con exportación a CSV.

Se parte del último push de la rama `Sprint_1` y se trabaja sobre la rama
`Sprint_2`.

## Estructura del proyecto

```
book_manager/
├── src/
│   └── book_manager/
│       ├── database/connection.py        # ConexionDB + Transaccion (Ej. 02 y 03)
│       ├── entities/entities.py          # Entidades del dominio (Sprint 1)
│       ├── models/models.py              # Tablas ORM con relaciones (Ej. 04)
│       ├── preload_data/preload_data.py  # Datos iniciales -> CSV de origen
│       ├── repositories/repositories.py  # CRUD sobre base de datos (Ej. 06)
│       ├── services/services.py          # Lógica de negocio + API (Ej. 07)
│       ├── migrations/
│       │   ├── migrations.py             # Migración CSV -> DB + .sql (Ej. 05)
│       │   ├── csv/                      # Archivos de origen (TP1)
│       │   └── sql/                      # Scripts generados en la migración
│       ├── ui/console.py                 # Interfaz de consola (Ej. 08)
│       └── main.py                       # Punto de entrada
├── .env                                  # API_URL y DATABASE_URL
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

## Modelo de datos

```
generos ──┐                    monedas ──┬── precios ── libros ── stock
editoriales ┴── libros                   └── tipos_cotizacion ── cotizaciones
```

- `tipos_cotizacion` incorpora `moneda_id`: un tipo de cambio pertenece a
  una moneda (el dólar tiene Oficial, Blue, MEP, CCL...; el euro o el real
  tienen su tipo Oficial). Los CSV del TP1 no tenían esa columna: la
  migración asigna USD.
- `cotizaciones` conserva el histórico por tipo y fecha (clave compuesta).

## Cómo ejecutar

Instalar las dependencias y configurar el `.env`:

```bash
pip install -r requirements.txt
```

```
API_URL=https://dolarapi.com/v1/dolares
API_URL_COTIZACIONES=https://dolarapi.com/v1/cotizaciones
DATABASE_URL=sqlite:///book_manager.db
```

Desde la terminal, parado en `src/`:

```bash
cd src
python -m book_manager.main
```

Desde un notebook (Google Colab):

```python
from book_manager.main import main
main(import_default_data=False)   # True regenera los CSV y vuelve a migrar
```

En la primera ejecución (base vacía) el sistema crea las tablas, migra los
CSV de `migrations/csv` y genera los scripts en `migrations/sql`.

La migración también puede ejecutarse por separado:

```python
from book_manager.migrations.migrations import migrar_datos
migrar_datos("src/book_manager/migrations/csv", "src/book_manager/migrations/sql")
```

## Menú del sistema

1-8. ABM (Listar / Alta / Modificar / Baja) de Libros, Géneros, Editoriales,
     Monedas, Tipos de cotización, Precios, Stock y Cotizaciones.
9. Reportes: catálogo valuado, cotizar un libro, stock bajo mínimo, valor
   del inventario, histórico de cotizaciones, lista bimonetaria y
   exportación.
10. **Obtener las cotizaciones por API**: descarga y registra en la base las
    cotizaciones del día (dólar por tipo y otras monedas).
11. **Lista de precios bimonetaria**: precios en pesos y en otra moneda
    seleccionada (USD según tipo, EUR, BRL, CLP, UYU...).
12. **Exportar precios a CSV**: una columna por cada moneda/tipo con
    cotización registrada (`exports/precios_todas_las_monedas.csv`).
