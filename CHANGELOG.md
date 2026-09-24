# Changelog

Los cambios más recientes aparecen primero. Cada ejercicio corresponde a un
día de trabajo (commit `"Día X: ..."`).

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
