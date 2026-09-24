# Changelog

Los cambios más recientes aparecen primero. Cada ejercicio corresponde a un
día de trabajo (commit `"Día X: ..."`).

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
