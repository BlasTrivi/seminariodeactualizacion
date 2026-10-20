# Changelog

Los cambios más recientes aparecen primero. Cada ejercicio corresponde a un
día de trabajo (commit `"Día X: ..."`).

# Sprint 3

## [Ejercicio 05]

- `ServicioComparadorPrecios.generar_reporte_excel` crea
  `reportes/reporte_precios_<fecha>.xlsx` con `openpyxl`:
  - Hoja **Comparación**: Libro, Precio interno, Precio web, Diferencia y
    Fecha de extracción (más diferencia %, ISBN, título y URL en la web),
    con formato de moneda, fecha, filtros y colores según la diferencia.
  - Hoja **Resultados web**: los 10 resultados de cada búsqueda con
    formas de pago y precio, URL de la imagen y descripción.

## [Ejercicio 04]

- `ServicioComparadorPrecios`: compara el precio interno (en pesos; los
  precios de lista en USD se convierten con el dólar Oficial o el tipo
  elegido) con el precio web del resultado seleccionado de cada libro.
- `ComparacionPrecio` calcula la diferencia en pesos y en porcentaje e
  indica si el competidor es más barato o más caro.
- `generar_alertas_csv(umbral_porcentual)`: el usuario ingresa la
  diferencia (%) antes de cada ejecución del scraper y se genera
  `reportes/alertas/alertas_<fecha>.csv` con los libros que la superan
  (UTF-8 con BOM para abrirlo directo en Excel).
- `reportes/.gitignore` para no versionar los archivos generados.

## [Ejercicio 03]

- Proyecto Scrapy en `scraper/` (`scrapy.cfg`, `settings.py`, `items.py`,
  `loaders.py`, `pipelines.py`, `spiders/cuspide.py`, `runner.py`).
- `CuspideSpider` busca por título **solo los libros de nuestro catálogo**
  (leídos de la base) y procesa los 10 primeros resultados de cada
  búsqueda: precio (ARS y U$s), URL de la imagen, formas de pago con su
  precio, descripción detallada, ISBN, título y autor. Si una búsqueda no
  devuelve resultados se reintenta con el título simplificado.
- Item Loader `LibroCuspideLoader` con procesadores de entrada/salida
  (limpieza de textos, precios con formato argentino, URLs absolutas,
  nombres de medios de pago).
- Pipelines: `ValidacionPipeline`, `FormasPagoPipeline`,
  `CoincidenciaPipeline` (puntaje por ISBN, título y autor) y
  `BaseDatosPipeline` (guarda en `precios_web` y marca el mejor resultado
  de cada libro).
- Nueva entidad `PrecioWeb`, tabla `precios_web` (`PrecioWebModel`) y
  `RepositorioPrecioWeb`; alias `CotizacionDolarModel`.
- `ServicioScraping.ejecutar_scraping` corre el spider en un proceso
  aparte (el reactor de Twisted no se puede reiniciar) y devuelve el
  resumen de la ejecución; los resultados también quedan en
  `reportes/scraping/*.json`.

## [Ejercicio 02]

- `migrations/migrations.py`: nueva función `cargar_datos_desde_sql(carpeta_sqls)`
  que crea las tablas, vacía los datos previos y ejecuta en una sola
  transacción los scripts `01_...sql` a `08_...sql` generados en la
  migración (el esquema `00_esquema.sql` se omite porque depende del
  dialecto; las tablas las crea SQLAlchemy).
- `CargadorSQL.sentencias` separa cada script respetando los textos entre
  comillas y los comentarios `--`.
- `main.py`: si la base está vacía se carga desde los `.sql`; si no hay
  scripts se migran los CSV como en el Sprint 2.

## [Ejercicio 01]

- Se crea la rama `Sprint_3` a partir del último push de `Sprint_2`.
- Nueva estructura: paquete `scraper/` (proyecto Scrapy) y carpeta
  `reportes/` para las alertas CSV y los reportes Excel.
- `.env` incorpora `CUSPIDE_URL`; `requirements.txt` suma `scrapy` y
  `openpyxl`.
- `README.md` actualizado con el objetivo y el contexto del Sprint 3.

# Sprint 2

## [Ejercicio 08]

- Se agregan al menú principal de `ui/console.py` las opciones: *Obtener
  las cotizaciones por API*, *Lista de precios bimonetaria* (pesos y otra
  moneda seleccionada) y *Exportar precios a CSV* para todas las monedas
  con cotización (también disponibles en el menú de Reportes).
- El ABM de tipos de cotización pide y muestra la moneda a la que
  pertenece cada tipo.
- Se completa el notebook de entrega `02_Book_Manager_Grupo_15.ipynb`.

## [Ejercicio 07]

- Se crea el archivo `.env` con `API_URL`, `API_URL_COTIZACIONES` y
  `DATABASE_URL`; las variables se leen con `python-dotenv`.
- `ClienteCotizacionesAPI` descarga las cotizaciones con `requests`.
- `ServicioCotizacionDolar.obtener_cotizaciones` busca, descarga y registra
  en la base las cotizaciones (crea la moneda y el tipo si no existen;
  actualiza la cotización del día si ya estaba cargada).
- `ServicioCotizador`: `lista_precios_bimonetaria`, `exportar_precios_csv`
  y `monedas_con_cotizacion`.
- `requirements.txt` con SQLAlchemy, python-dotenv y requests.

## [Ejercicio 06]

- `repositories/repositories.py` pasa de CSV a base de datos: se mantienen
  las interfaces del enunciado y las firmas usadas por los servicios.
- `RepositorioSQL` genérico (CRUD, `contar`, `vaciar`) con conversión
  entidad <-> modelo; repositorios de `Stock` y `Cotizacion` con clave
  natural; `Repositorios.desde_conexion`.
- Los servicios usan `moneda_id` del tipo de cotización (unicidad por
  moneda, borrado bloqueado) y la baja de libro elimina precios y stock
  antes que el libro para respetar las claves foráneas.

## [Ejercicio 05]

- Se crea `migrations/migrations.py` con `migrar_datos(carpeta_csvs,
  carpeta_sqls)`: lee los CSV del TP1, puebla la base a través de los
  repositorios y genera un `.sql` por tabla (más `00_esquema.sql` con el
  DDL) en `migrations/sql`.
- `preload_data.py` pasa a generar los archivos CSV de origen.

## [Ejercicio 04]

- Se crea `models/models.py` con las tablas `generos`, `editoriales`,
  `monedas`, `tipos_cotizacion`, `libros`, `precios`, `stock` y
  `cotizaciones`: tipos de datos, claves primarias y foráneas,
  restricciones de unicidad y relaciones (`relationship`) con cascada.
- Normalización: `TipoCotizacion` incorpora `moneda_id` (entidad y modelo).

## [Ejercicio 03]

- Se agrega a `database/connection.py` el context manager `Transaccion`
  (`__enter__` / `__exit__`): commit al terminar el bloque, rollback ante
  excepciones y cierre de la sesión.

## [Ejercicio 02]

- Se crea `database/connection.py` con la clase `ConexionDB`: lee
  `DATABASE_URL` del `.env`, construye el motor de SQLAlchemy, crea o
  elimina las tablas, prueba la conexión y entrega sesiones.

## [Ejercicio 01]

- Se crea la rama `Sprint_2` a partir de `Sprint_1`.
- Nueva estructura de directorios: `database/`, `models/`,
  `migrations/sql/`, `.env`; se actualizan `README.md` y `.gitignore`.

# Sprint 1

## [Ejercicio 07]

- Se crea `src/book_manager/main.py` con la función `main(import_default_data)`
  que construye los repositorios y los servicios y lanza la consola.
- Carga automática de los datos iniciales cuando falta algún archivo CSV.
- Se completa el notebook de entrega `01_Book_Manager_Grupo_15.ipynb`.

## [Ejercicio 06]

- Se crea `src/book_manager/ui/console.py` con la clase `ConsolaUI`: menú
  principal, submenú ABM (Listar / Alta / Modificar / Baja) para cada entidad
  y menú de reportes.
- Helpers de entrada con validación (`_pedir_texto`, `_pedir_int`,
  `_pedir_float`, `_pedir_fecha`) e impresión de tablas.
- Operaciones extra: búsqueda y detalle de libros, ingreso y egreso de stock.

## [Ejercicio 05]

- Se crea `src/book_manager/preload_data/preload_data.py` con los datos
  iniciales (mínimo 10 registros por entidad) y la función
  `cargar_datos_iniciales`.
- Se generan los archivos CSV en `src/book_manager/migrations/csv/`.

## [Ejercicio 04]

- Se crea `src/book_manager/services/services.py` con `ServicioBase` y un
  servicio por entidad con las reglas de negocio: unicidad de nombres, códigos
  e ISBN; integridad referencial; borrado bloqueado (género, editorial, moneda,
  tipo de cotización en uso) y en cascada (libro con sus precios y stock).
- Se agrega `ServicioCotizador` con los reportes de valuación: catálogo
  valuado, cotización de un libro y valor total del inventario.
- Se agrega el contenedor `Servicios` con inyección de repositorios.

## [Ejercicio 03]

- Se crea `src/book_manager/repositories/repositories.py` con las interfaces
  `IRepositorio`, `IRepositorioStock` e `IRepositorioCotizacionDolar`.
- Implementación genérica `RepositorioCSV` con persistencia en archivos CSV y
  CRUD completo para todas las entidades; repositorios de `Stock` y
  `CotizacionDolar` con clave natural.
- Se agrega el contenedor `Repositorios` con la fábrica `desde_directorio`.

## [Ejercicio 02]

- Se crea `src/book_manager/entities/entities.py` con las entidades `Genero`,
  `Editorial`, `Moneda`, `TipoCotizacion`, `Libro`, `Precio`, `Stock` y
  `CotizacionDolar`.
- Encapsulamiento mediante atributos privados y propiedades con validación;
  serialización a/desde diccionario para la persistencia.

## [Ejercicio 01]

- Inicialización del repositorio y creación de la rama `Sprint_1`.
- Estructura de directorios del proyecto, `README.md`, `CHANGELOG.md`,
  `requirements.txt` y `.gitignore`.
