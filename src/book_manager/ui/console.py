"""Interfaz de consola (CLI) de Book Manager.

La clase ``ConsolaUI`` muestra un menú principal con un submenú de
ABM (Listar / Alta / Modificar / Baja) por cada entidad y un menú de
reportes. Toda la lógica de negocio queda en los servicios; acá solo se
piden datos por teclado, se validan los formatos y se muestran tablas.

Sprint 2 (Ejercicio 08): se agregan al menú principal las opciones para
obtener las cotizaciones por API, ver la lista de precios bimonetaria
(pesos y otra moneda seleccionada) y exportar los precios a CSV para
todas las monedas con cotización.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from book_manager.database.connection import RAIZ_PROYECTO
from book_manager.entities.entities import (
    CotizacionDolar, Editorial, Genero, Libro, Moneda, Precio, Stock,
    TipoCotizacion, fecha_desde,
)
from book_manager.services.services import (
    CODIGO_DOLAR, ColumnaMoneda, Servicios,
)

Accion = Callable[[], None]
Opciones = Dict[str, Tuple[str, Accion]]

ANCHO = 72
CARPETA_EXPORTACION = RAIZ_PROYECTO / "exports"
ARCHIVO_EXPORTACION = "precios_todas_las_monedas.csv"


def formato_importe(valor: float) -> str:
    """Formatea un importe con separador de miles y coma decimal."""
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


class ConsolaUI:
    """Menús interactivos que operan sobre los CRUD de cada entidad."""

    def __init__(self, servicios: Servicios) -> None:
        self._s = servicios

    # ------------------------------------------------------------------
    # Menú principal
    # ------------------------------------------------------------------

    def ejecutar(self) -> None:
        """Bucle principal; termina cuando el usuario elige salir."""
        opciones: Opciones = {
            "1": ("Libros", self._menu_libros),
            "2": ("Géneros", self._menu_generos),
            "3": ("Editoriales", self._menu_editoriales),
            "4": ("Monedas", self._menu_monedas),
            "5": ("Tipos de cotización", self._menu_tipos_cotizacion),
            "6": ("Precios", self._menu_precios),
            "7": ("Stock", self._menu_stock),
            "8": ("Cotizaciones", self._menu_cotizaciones),
            "9": ("Reportes", self._menu_reportes),
            "10": ("Obtener las cotizaciones por API",
                   self._obtener_cotizaciones_api),
            "11": ("Lista de precios bimonetaria (pesos y otra moneda)",
                   self._lista_precios_bimonetaria),
            "12": ("Exportar precios a CSV (todas las monedas)",
                   self._exportar_precios_csv),
        }
        self._titulo("BOOK MANAGER - Sprint 2")
        self._bucle_menu("Menú principal", opciones, "Salir")
        print("Hasta luego.")

    def _bucle_menu(self, titulo: str, opciones: Opciones,
                    texto_salida: str = "Volver") -> None:
        """Muestra las opciones y ejecuta la elegida hasta que se sale."""
        while True:
            print(f"\n--- {titulo} ---")
            for clave, (nombre, _) in opciones.items():
                print(f"{clave}. {nombre}")
            print(f"0. {texto_salida}")
            eleccion = input("Opción: ").strip()
            if eleccion == "0":
                return
            if eleccion not in opciones:
                print("Opción inválida, intente nuevamente.")
                continue
            try:
                opciones[eleccion][1]()
            except ValueError as error:
                print(f"Error: {error}")

    def _menu_abm(self, titulo: str, listar: Accion, alta: Accion,
                  modificar: Accion, baja: Accion,
                  extras: Optional[Opciones] = None) -> None:
        opciones: Opciones = {
            "1": ("Listar", listar),
            "2": ("Alta", alta),
            "3": ("Modificar", modificar),
            "4": ("Baja", baja),
        }
        if extras:
            opciones.update(extras)
        self._bucle_menu(titulo, opciones)

    # ------------------------------------------------------------------
    # Helpers de entrada y salida
    # ------------------------------------------------------------------

    @staticmethod
    def _titulo(texto: str) -> None:
        print("\n" + "=" * ANCHO)
        print(texto.center(ANCHO))
        print("=" * ANCHO)

    @staticmethod
    def _pedir_texto(mensaje: str, obligatorio: bool = True,
                     actual: Optional[str] = None) -> str:
        """Pide un texto; con ``actual`` el Enter conserva el valor."""
        sufijo = f" [{actual}]" if actual is not None else ""
        while True:
            texto = input(f"{mensaje}{sufijo}: ").strip()
            if texto:
                return texto
            if actual is not None:
                return actual
            if not obligatorio:
                return ""
            print("El valor es obligatorio.")

    def _pedir_int(self, mensaje: str,
                   actual: Optional[int] = None) -> int:
        while True:
            texto = self._pedir_texto(
                mensaje, actual=None if actual is None else str(actual))
            try:
                return int(texto)
            except ValueError:
                print("Debe ingresar un número entero.")

    def _pedir_float(self, mensaje: str,
                     actual: Optional[float] = None) -> float:
        while True:
            texto = self._pedir_texto(
                mensaje, actual=None if actual is None else f"{actual:.2f}")
            try:
                return float(texto.replace(",", "."))
            except ValueError:
                print("Debe ingresar un número (use punto decimal).")

    def _pedir_fecha(self, mensaje: str,
                     actual: Optional[datetime.date] = None
                     ) -> datetime.date:
        """Pide una fecha AAAA-MM-DD; Enter toma la actual o la de hoy."""
        por_defecto = actual or datetime.date.today()
        while True:
            texto = self._pedir_texto(
                f"{mensaje} (AAAA-MM-DD)", actual=por_defecto.isoformat())
            try:
                return fecha_desde(texto)
            except ValueError as error:
                print(error)

    @staticmethod
    def _confirmar(mensaje: str) -> bool:
        return input(f"{mensaje} (s/n): ").strip().lower() == "s"

    @staticmethod
    def _imprimir_tabla(encabezados: Sequence[str],
                        filas: Sequence[Sequence[object]]) -> None:
        """Imprime una tabla de texto con anchos calculados."""
        if not filas:
            print("(sin registros)")
            return
        celdas = [[str(valor) for valor in fila] for fila in filas]
        anchos = [len(titulo) for titulo in encabezados]
        for fila in celdas:
            for posicion, valor in enumerate(fila):
                anchos[posicion] = max(anchos[posicion], len(valor))
        linea = "  ".join(t.ljust(a) for t, a in zip(encabezados, anchos))
        print(linea)
        print("-" * len(linea))
        for fila in celdas:
            print("  ".join(v.ljust(a) for v, a in zip(fila, anchos)))
        print(f"{len(filas)} registro(s).")

    def _nombre_genero(self, genero_id: int) -> str:
        try:
            return self._s.generos.obtener(genero_id).nombre
        except ValueError:
            return f"? ({genero_id})"

    def _nombre_editorial(self, editorial_id: int) -> str:
        try:
            return self._s.editoriales.obtener(editorial_id).nombre
        except ValueError:
            return f"? ({editorial_id})"

    def _nombre_libro(self, libro_id: int) -> str:
        try:
            return self._s.libros.obtener(libro_id).titulo
        except ValueError:
            return f"? ({libro_id})"

    def _codigo_moneda(self, moneda_id: int) -> str:
        try:
            return self._s.monedas.obtener(moneda_id).codigo
        except ValueError:
            return f"? ({moneda_id})"

    def _nombre_tipo(self, tipo_id: int) -> str:
        try:
            tipo = self._s.tipos_cotizacion.obtener(tipo_id)
            return f"{self._codigo_moneda(tipo.moneda_id)} {tipo.nombre}"
        except ValueError:
            return f"? ({tipo_id})"

    # ------------------------------------------------------------------
    # Géneros
    # ------------------------------------------------------------------

    def _menu_generos(self) -> None:
        self._menu_abm("Géneros", self._listar_generos, self._alta_genero,
                       self._modificar_genero, self._baja_genero)

    def _listar_generos(self) -> None:
        filas = [(g.id, g.nombre, g.descripcion)
                 for g in self._s.generos.listar()]
        self._imprimir_tabla(("ID", "Nombre", "Descripción"), filas)

    def _alta_genero(self) -> None:
        nombre = self._pedir_texto("Nombre")
        descripcion = self._pedir_texto("Descripción", obligatorio=False)
        genero = self._s.generos.crear(Genero(nombre, descripcion))
        print(f"Género creado con id {genero.id}.")

    def _modificar_genero(self) -> None:
        self._listar_generos()
        genero = self._s.generos.obtener(self._pedir_int("ID a modificar"))
        genero.nombre = self._pedir_texto("Nombre", actual=genero.nombre)
        genero.descripcion = self._pedir_texto(
            "Descripción", obligatorio=False, actual=genero.descripcion)
        self._s.generos.actualizar(genero)
        print("Género actualizado.")

    def _baja_genero(self) -> None:
        self._listar_generos()
        genero = self._s.generos.obtener(self._pedir_int("ID a eliminar"))
        if self._confirmar(f"¿Eliminar '{genero.nombre}'?"):
            self._s.generos.eliminar(genero.id or 0)
            print("Género eliminado.")

    # ------------------------------------------------------------------
    # Editoriales
    # ------------------------------------------------------------------

    def _menu_editoriales(self) -> None:
        self._menu_abm("Editoriales", self._listar_editoriales,
                       self._alta_editorial, self._modificar_editorial,
                       self._baja_editorial)

    def _listar_editoriales(self) -> None:
        filas = [(e.id, e.nombre, e.pais)
                 for e in self._s.editoriales.listar()]
        self._imprimir_tabla(("ID", "Nombre", "País"), filas)

    def _alta_editorial(self) -> None:
        nombre = self._pedir_texto("Nombre")
        pais = self._pedir_texto("País", obligatorio=False)
        editorial = self._s.editoriales.crear(Editorial(nombre, pais))
        print(f"Editorial creada con id {editorial.id}.")

    def _modificar_editorial(self) -> None:
        self._listar_editoriales()
        editorial = self._s.editoriales.obtener(
            self._pedir_int("ID a modificar"))
        editorial.nombre = self._pedir_texto("Nombre",
                                             actual=editorial.nombre)
        editorial.pais = self._pedir_texto("País", obligatorio=False,
                                           actual=editorial.pais)
        self._s.editoriales.actualizar(editorial)
        print("Editorial actualizada.")

    def _baja_editorial(self) -> None:
        self._listar_editoriales()
        editorial = self._s.editoriales.obtener(
            self._pedir_int("ID a eliminar"))
        if self._confirmar(f"¿Eliminar '{editorial.nombre}'?"):
            self._s.editoriales.eliminar(editorial.id or 0)
            print("Editorial eliminada.")

    # ------------------------------------------------------------------
    # Monedas
    # ------------------------------------------------------------------

    def _menu_monedas(self) -> None:
        self._menu_abm("Monedas", self._listar_monedas, self._alta_moneda,
                       self._modificar_moneda, self._baja_moneda)

    def _listar_monedas(self) -> None:
        filas = [(m.id, m.codigo, m.nombre, m.simbolo)
                 for m in self._s.monedas.listar()]
        self._imprimir_tabla(("ID", "Código", "Nombre", "Símbolo"), filas)

    def _alta_moneda(self) -> None:
        codigo = self._pedir_texto("Código (3 letras)")
        nombre = self._pedir_texto("Nombre")
        simbolo = self._pedir_texto("Símbolo", obligatorio=False)
        moneda = self._s.monedas.crear(Moneda(codigo, nombre, simbolo))
        print(f"Moneda creada con id {moneda.id}.")

    def _modificar_moneda(self) -> None:
        self._listar_monedas()
        moneda = self._s.monedas.obtener(self._pedir_int("ID a modificar"))
        moneda.codigo = self._pedir_texto("Código", actual=moneda.codigo)
        moneda.nombre = self._pedir_texto("Nombre", actual=moneda.nombre)
        moneda.simbolo = self._pedir_texto("Símbolo", obligatorio=False,
                                           actual=moneda.simbolo)
        self._s.monedas.actualizar(moneda)
        print("Moneda actualizada.")

    def _baja_moneda(self) -> None:
        self._listar_monedas()
        moneda = self._s.monedas.obtener(self._pedir_int("ID a eliminar"))
        if self._confirmar(f"¿Eliminar '{moneda.codigo}'?"):
            self._s.monedas.eliminar(moneda.id or 0)
            print("Moneda eliminada.")

    # ------------------------------------------------------------------
    # Tipos de cotización
    # ------------------------------------------------------------------

    def _menu_tipos_cotizacion(self) -> None:
        self._menu_abm("Tipos de cotización", self._listar_tipos,
                       self._alta_tipo, self._modificar_tipo,
                       self._baja_tipo)

    def _listar_tipos(self) -> None:
        filas = [(t.id, self._codigo_moneda(t.moneda_id), t.nombre,
                  t.descripcion)
                 for t in self._s.tipos_cotizacion.listar()]
        self._imprimir_tabla(("ID", "Moneda", "Nombre", "Descripción"), filas)

    def _alta_tipo(self) -> None:
        self._listar_monedas()
        moneda_id = self._pedir_int("ID de moneda")
        nombre = self._pedir_texto("Nombre")
        descripcion = self._pedir_texto("Descripción", obligatorio=False)
        tipo = self._s.tipos_cotizacion.crear(
            TipoCotizacion(nombre, descripcion, moneda_id))
        print(f"Tipo de cotización creado con id {tipo.id}.")

    def _modificar_tipo(self) -> None:
        self._listar_tipos()
        tipo = self._s.tipos_cotizacion.obtener(
            self._pedir_int("ID a modificar"))
        tipo.nombre = self._pedir_texto("Nombre", actual=tipo.nombre)
        tipo.descripcion = self._pedir_texto(
            "Descripción", obligatorio=False, actual=tipo.descripcion)
        tipo.moneda_id = self._pedir_int("ID de moneda",
                                         actual=tipo.moneda_id)
        self._s.tipos_cotizacion.actualizar(tipo)
        print("Tipo de cotización actualizado.")

    def _baja_tipo(self) -> None:
        self._listar_tipos()
        tipo = self._s.tipos_cotizacion.obtener(
            self._pedir_int("ID a eliminar"))
        if self._confirmar(f"¿Eliminar '{tipo.nombre}'?"):
            self._s.tipos_cotizacion.eliminar(tipo.id or 0)
            print("Tipo de cotización eliminado.")

    # ------------------------------------------------------------------
    # Libros
    # ------------------------------------------------------------------

    def _menu_libros(self) -> None:
        extras: Opciones = {
            "5": ("Buscar por título", self._buscar_libros),
            "6": ("Ver detalle", self._detalle_libro),
        }
        self._menu_abm("Libros", self._listar_libros, self._alta_libro,
                       self._modificar_libro, self._baja_libro, extras)

    def _tabla_libros(self, libros: List[Libro]) -> None:
        filas = [(libro.id, libro.isbn, libro.titulo, libro.autor,
                  self._nombre_editorial(libro.editorial_id),
                  self._nombre_genero(libro.genero_id), libro.anio)
                 for libro in libros]
        self._imprimir_tabla(
            ("ID", "ISBN", "Título", "Autor", "Editorial", "Género", "Año"),
            filas)

    def _listar_libros(self) -> None:
        self._tabla_libros(self._s.libros.listar())

    def _buscar_libros(self) -> None:
        texto = self._pedir_texto("Texto a buscar en el título")
        self._tabla_libros(self._s.libros.buscar_por_titulo(texto))

    def _alta_libro(self) -> None:
        isbn = self._pedir_texto("ISBN")
        titulo = self._pedir_texto("Título")
        autor = self._pedir_texto("Autor")
        self._listar_editoriales()
        editorial_id = self._pedir_int("ID de editorial")
        self._listar_generos()
        genero_id = self._pedir_int("ID de género")
        anio = self._pedir_int("Año de publicación")
        libro = self._s.libros.crear(
            Libro(isbn, titulo, autor, editorial_id, genero_id, anio))
        print(f"Libro creado con id {libro.id}.")
        if self._confirmar("¿Cargar stock inicial ahora?"):
            cantidad = self._pedir_int("Cantidad", actual=0)
            minimo = self._pedir_int("Cantidad mínima", actual=0)
            self._s.stock.crear(Stock(libro.id or 0, cantidad, minimo))
            print("Stock cargado.")

    def _modificar_libro(self) -> None:
        self._listar_libros()
        libro = self._s.libros.obtener(self._pedir_int("ID a modificar"))
        libro.isbn = self._pedir_texto("ISBN", actual=libro.isbn)
        libro.titulo = self._pedir_texto("Título", actual=libro.titulo)
        libro.autor = self._pedir_texto("Autor", actual=libro.autor)
        libro.editorial_id = self._pedir_int("ID de editorial",
                                             actual=libro.editorial_id)
        libro.genero_id = self._pedir_int("ID de género",
                                          actual=libro.genero_id)
        libro.anio = self._pedir_int("Año", actual=libro.anio)
        self._s.libros.actualizar(libro)
        print("Libro actualizado.")

    def _baja_libro(self) -> None:
        self._listar_libros()
        libro = self._s.libros.obtener(self._pedir_int("ID a eliminar"))
        if self._confirmar(
                f"¿Eliminar '{libro.titulo}' con sus precios y stock?"):
            self._s.libros.eliminar(libro.id or 0)
            print("Libro eliminado.")

    def _detalle_libro(self) -> None:
        self._listar_libros()
        detalle = self._s.libros.obtener_detalle(self._pedir_int("ID"))
        libro = detalle.libro
        print(f"\n{libro.titulo} - {libro.autor} ({libro.anio})")
        print(f"ISBN: {libro.isbn}")
        print(f"Editorial: {detalle.editorial or '-'}")
        print(f"Género: {detalle.genero or '-'}")
        if detalle.precios:
            for precio in detalle.precios:
                codigo = self._codigo_moneda(precio.moneda_id)
                print(f"Precio: {codigo} {formato_importe(precio.valor)}")
        else:
            print("Precio: sin cargar")
        if detalle.stock:
            aviso = " (BAJO MÍNIMO)" if detalle.stock.esta_bajo_minimo() \
                else ""
            print(f"Stock: {detalle.stock.cantidad} unidades "
                  f"(mínimo {detalle.stock.cantidad_minima}){aviso}")
        else:
            print("Stock: sin cargar")

    # ------------------------------------------------------------------
    # Precios
    # ------------------------------------------------------------------

    def _menu_precios(self) -> None:
        self._menu_abm("Precios", self._listar_precios, self._alta_precio,
                       self._modificar_precio, self._baja_precio)

    def _listar_precios(self) -> None:
        filas = [(p.id, self._nombre_libro(p.libro_id),
                  self._codigo_moneda(p.moneda_id),
                  formato_importe(p.valor))
                 for p in self._s.precios.listar()]
        self._imprimir_tabla(("ID", "Libro", "Moneda", "Valor"), filas)

    def _alta_precio(self) -> None:
        self._listar_libros()
        libro_id = self._pedir_int("ID de libro")
        self._listar_monedas()
        moneda_id = self._pedir_int("ID de moneda")
        valor = self._pedir_float("Valor")
        precio = self._s.precios.crear(Precio(libro_id, moneda_id, valor))
        print(f"Precio creado con id {precio.id}.")

    def _modificar_precio(self) -> None:
        self._listar_precios()
        precio = self._s.precios.obtener(self._pedir_int("ID a modificar"))
        precio.moneda_id = self._pedir_int("ID de moneda",
                                           actual=precio.moneda_id)
        precio.valor = self._pedir_float("Valor", actual=precio.valor)
        self._s.precios.actualizar(precio)
        print("Precio actualizado.")

    def _baja_precio(self) -> None:
        self._listar_precios()
        precio = self._s.precios.obtener(self._pedir_int("ID a eliminar"))
        if self._confirmar("¿Eliminar el precio?"):
            self._s.precios.eliminar(precio.id or 0)
            print("Precio eliminado.")

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    def _menu_stock(self) -> None:
        extras: Opciones = {
            "5": ("Ingreso de unidades", self._ingreso_stock),
            "6": ("Egreso de unidades (venta)", self._egreso_stock),
        }
        self._menu_abm("Stock", self._listar_stock, self._alta_stock,
                       self._modificar_stock, self._baja_stock, extras)

    def _listar_stock(self) -> None:
        filas = [(s.libro_id, self._nombre_libro(s.libro_id), s.cantidad,
                  s.cantidad_minima,
                  "BAJO" if s.esta_bajo_minimo() else "ok")
                 for s in self._s.stock.listar()]
        self._imprimir_tabla(
            ("Libro ID", "Libro", "Cantidad", "Mínimo", "Estado"), filas)

    def _alta_stock(self) -> None:
        self._listar_libros()
        libro_id = self._pedir_int("ID de libro")
        cantidad = self._pedir_int("Cantidad", actual=0)
        minimo = self._pedir_int("Cantidad mínima", actual=0)
        self._s.stock.crear(Stock(libro_id, cantidad, minimo))
        print("Stock creado.")

    def _modificar_stock(self) -> None:
        self._listar_stock()
        stock = self._s.stock.obtener(self._pedir_int("ID de libro"))
        stock.cantidad = self._pedir_int("Cantidad", actual=stock.cantidad)
        stock.cantidad_minima = self._pedir_int(
            "Cantidad mínima", actual=stock.cantidad_minima)
        self._s.stock.actualizar(stock)
        print("Stock actualizado.")

    def _baja_stock(self) -> None:
        self._listar_stock()
        stock = self._s.stock.obtener(self._pedir_int("ID de libro"))
        if self._confirmar("¿Eliminar el registro de stock?"):
            self._s.stock.eliminar(stock.libro_id)
            print("Stock eliminado.")

    def _ingreso_stock(self) -> None:
        self._listar_stock()
        libro_id = self._pedir_int("ID de libro")
        unidades = self._pedir_int("Unidades que ingresan")
        stock = self._s.stock.ingresar(libro_id, unidades)
        print(f"Stock actual: {stock.cantidad} unidades.")

    def _egreso_stock(self) -> None:
        self._listar_stock()
        libro_id = self._pedir_int("ID de libro")
        unidades = self._pedir_int("Unidades que egresan")
        stock = self._s.stock.egresar(libro_id, unidades)
        print(f"Stock actual: {stock.cantidad} unidades.")

    # ------------------------------------------------------------------
    # Cotizaciones
    # ------------------------------------------------------------------

    def _menu_cotizaciones(self) -> None:
        extras: Opciones = {
            "5": ("Obtener las cotizaciones por API",
                  self._obtener_cotizaciones_api),
        }
        self._menu_abm("Cotizaciones", self._listar_cotizaciones,
                       self._alta_cotizacion, self._modificar_cotizacion,
                       self._baja_cotizacion, extras)

    def _tabla_cotizaciones(self, cotizaciones: List[CotizacionDolar]
                            ) -> None:
        filas = [(c.tipo_id, self._nombre_tipo(c.tipo_id), c.fecha,
                  formato_importe(c.compra), formato_importe(c.venta))
                 for c in cotizaciones]
        self._imprimir_tabla(
            ("Tipo ID", "Tipo", "Fecha", "Compra", "Venta"), filas)

    def _listar_cotizaciones(self) -> None:
        self._tabla_cotizaciones(self._s.cotizaciones.listar())

    def _alta_cotizacion(self) -> None:
        self._listar_tipos()
        tipo_id = self._pedir_int("ID de tipo de cotización")
        fecha = self._pedir_fecha("Fecha")
        compra = self._pedir_float("Compra")
        venta = self._pedir_float("Venta")
        self._s.cotizaciones.crear(
            CotizacionDolar(tipo_id, fecha, compra, venta))
        print("Cotización registrada.")

    def _modificar_cotizacion(self) -> None:
        self._listar_cotizaciones()
        tipo_id = self._pedir_int("ID de tipo de cotización")
        fecha = self._pedir_fecha("Fecha")
        cotizacion = self._s.cotizaciones.obtener(tipo_id, fecha)
        cotizacion.compra = self._pedir_float("Compra",
                                              actual=cotizacion.compra)
        cotizacion.venta = self._pedir_float("Venta",
                                             actual=cotizacion.venta)
        self._s.cotizaciones.actualizar(cotizacion)
        print("Cotización actualizada.")

    def _baja_cotizacion(self) -> None:
        self._listar_cotizaciones()
        tipo_id = self._pedir_int("ID de tipo de cotización")
        fecha = self._pedir_fecha("Fecha")
        self._s.cotizaciones.obtener(tipo_id, fecha)
        if self._confirmar("¿Eliminar la cotización?"):
            self._s.cotizaciones.eliminar(tipo_id, fecha)
            print("Cotización eliminada.")

    # ------------------------------------------------------------------
    # Sprint 2 - Ejercicio 08: API, lista bimonetaria y exportación
    # ------------------------------------------------------------------

    def _obtener_cotizaciones_api(self) -> None:
        """Descarga las cotizaciones de la API y las registra en la base."""
        print(f"Consultando {self._s.cotizaciones.cliente_api.url} ...")
        importadas = self._s.cotizaciones.obtener_cotizaciones()
        filas = [(i.moneda.codigo, i.tipo.nombre, i.cotizacion.fecha,
                  formato_importe(i.cotizacion.compra),
                  formato_importe(i.cotizacion.venta),
                  "alta" if i.nueva else "actualizada")
                 for i in importadas]
        self._imprimir_tabla(
            ("Moneda", "Tipo", "Fecha", "Compra", "Venta", "Operación"),
            filas)
        nuevas = sum(1 for i in importadas if i.nueva)
        print(f"Cotizaciones registradas: {nuevas} nueva(s), "
              f"{len(importadas) - nuevas} actualizada(s).")

    def _tabla_columnas(self, columnas: Sequence[ColumnaMoneda]) -> None:
        filas = [(c.tipo.id, c.moneda.codigo, c.tipo.nombre,
                  c.cotizacion.fecha, formato_importe(c.cotizacion.venta))
                 for c in columnas]
        self._imprimir_tabla(
            ("Tipo ID", "Moneda", "Tipo", "Fecha", "Venta"), filas)

    def _pedir_tipo_dolar(self, columnas: Sequence[ColumnaMoneda]) -> int:
        """Pide el tipo de dólar que se usa para pasar a pesos."""
        dolares = [c for c in columnas if c.moneda.codigo == CODIGO_DOLAR]
        if not dolares:
            raise ValueError("No hay cotizaciones del dólar registradas.")
        print("\nTipo de dólar para valuar en pesos los precios en USD:")
        self._tabla_columnas(dolares)
        return self._pedir_int("ID de tipo de dólar",
                               actual=dolares[0].tipo.id)

    def _lista_precios_bimonetaria(self) -> None:
        """Precios de los libros en pesos y en otra moneda seleccionada."""
        columnas = self._s.cotizador.monedas_con_cotizacion()
        if not columnas:
            raise ValueError("No hay cotizaciones registradas: use la "
                             "opción 'Obtener las cotizaciones por API'.")
        print("\nMonedas y tipos de cotización disponibles:")
        self._tabla_columnas(columnas)
        tipo_moneda_id = self._pedir_int(
            "ID de tipo (moneda en la que se expresa la segunda columna)")
        tipo = self._s.tipos_cotizacion.obtener(tipo_moneda_id)
        moneda = self._s.monedas.obtener(tipo.moneda_id)
        if moneda.codigo == CODIGO_DOLAR:
            tipo_dolar_id = tipo_moneda_id
        else:
            tipo_dolar_id = self._pedir_tipo_dolar(columnas)
        lista = self._s.cotizador.lista_precios_bimonetaria(
            tipo_dolar_id, tipo_moneda_id)
        if not lista:
            print("(sin libros cotizables)")
            return
        cotizacion = lista[0].cotizacion
        print(f"\nLista de precios en ARS y {moneda.codigo} "
              f"({tipo.nombre}, cotización del {cotizacion.fecha}: "
              f"venta {formato_importe(cotizacion.venta)})")
        filas = [(p.libro.id, p.libro.titulo,
                  f"{p.moneda_lista.codigo} {formato_importe(p.precio.valor)}",
                  formato_importe(p.valor_ars),
                  formato_importe(p.valor_moneda))
                 for p in lista]
        self._imprimir_tabla(
            ("ID", "Título", "Precio de lista", "ARS", moneda.codigo), filas)

    def _exportar_precios_csv(self) -> None:
        """Exporta a CSV los precios en pesos y en todas las monedas."""
        columnas = self._s.cotizador.monedas_con_cotizacion()
        if not columnas:
            raise ValueError("No hay cotizaciones registradas: use la "
                             "opción 'Obtener las cotizaciones por API'.")
        tipo_dolar_id = self._pedir_tipo_dolar(columnas)
        ruta = Path(self._pedir_texto(
            "Archivo de destino",
            actual=str(CARPETA_EXPORTACION / ARCHIVO_EXPORTACION)))
        ruta, libros, monedas = self._s.cotizador.exportar_precios_csv(
            ruta, tipo_dolar_id)
        print(f"Se exportaron {libros} libro(s) en ARS y {monedas} "
              f"columna(s) de moneda/tipo a:\n  {ruta}")

    # ------------------------------------------------------------------
    # Reportes
    # ------------------------------------------------------------------

    def _menu_reportes(self) -> None:
        opciones: Opciones = {
            "1": ("Catálogo valuado según tipo de dólar",
                  self._reporte_catalogo_valuado),
            "2": ("Cotizar un libro", self._reporte_cotizar_libro),
            "3": ("Libros con stock bajo mínimo", self._reporte_stock_bajo),
            "4": ("Valor total del inventario",
                  self._reporte_valor_inventario),
            "5": ("Histórico de cotizaciones por tipo",
                  self._reporte_historico),
            "6": ("Lista de precios bimonetaria",
                  self._lista_precios_bimonetaria),
            "7": ("Exportar precios a CSV (todas las monedas)",
                  self._exportar_precios_csv),
        }
        self._bucle_menu("Reportes", opciones)

    def _pedir_tipo_cotizacion(self) -> int:
        self._listar_tipos()
        return self._pedir_int("ID de tipo de cotización")

    def _reporte_catalogo_valuado(self) -> None:
        tipo_id = self._pedir_tipo_cotizacion()
        cotizados = self._s.cotizador.catalogo_valuado(tipo_id)
        if cotizados:
            cotizacion = cotizados[0].cotizacion
            print(f"\nCotización {self._nombre_tipo(tipo_id)} del "
                  f"{cotizacion.fecha}: venta "
                  f"{formato_importe(cotizacion.venta)}")
        filas = [(c.libro.id, c.libro.titulo,
                  f"{c.moneda.codigo} {formato_importe(c.precio.valor)}",
                  formato_importe(c.valor_ars), formato_importe(c.valor_usd))
                 for c in cotizados]
        self._imprimir_tabla(
            ("ID", "Título", "Precio de lista", "En ARS", "En USD"), filas)

    def _reporte_cotizar_libro(self) -> None:
        self._listar_libros()
        libro_id = self._pedir_int("ID de libro")
        tipo_id = self._pedir_tipo_cotizacion()
        cotizado = self._s.cotizador.cotizar_libro(libro_id, tipo_id)
        print(f"\n{cotizado.libro.titulo}")
        print(f"Precio de lista: {cotizado.moneda.codigo} "
              f"{formato_importe(cotizado.precio.valor)}")
        print(f"Cotización {self._nombre_tipo(tipo_id)} "
              f"({cotizado.cotizacion.fecha}): venta "
              f"{formato_importe(cotizado.cotizacion.venta)}")
        print(f"Valor en ARS: $ {formato_importe(cotizado.valor_ars)}")
        print(f"Valor en USD: US$ {formato_importe(cotizado.valor_usd)}")

    def _reporte_stock_bajo(self) -> None:
        filas = [(libro.id, libro.titulo, stock.cantidad,
                  stock.cantidad_minima,
                  stock.cantidad_minima - stock.cantidad)
                 for libro, stock in self._s.stock.listar_bajo_minimo()]
        self._imprimir_tabla(
            ("ID", "Título", "Cantidad", "Mínimo", "Faltante"), filas)

    def _reporte_valor_inventario(self) -> None:
        tipo_id = self._pedir_tipo_cotizacion()
        total_ars, total_usd = self._s.cotizador.valor_inventario(tipo_id)
        print(f"\nValor del inventario ({self._nombre_tipo(tipo_id)}):")
        print(f"  ARS: $ {formato_importe(total_ars)}")
        print(f"  USD: US$ {formato_importe(total_usd)}")

    def _reporte_historico(self) -> None:
        tipo_id = self._pedir_tipo_cotizacion()
        historico = self._s.cotizaciones.listar_por_tipo(tipo_id)
        self._tabla_cotizaciones(historico)
        if len(historico) >= 2:
            variacion = historico[-1].venta - historico[0].venta
            porcentaje = variacion / historico[0].venta * 100
            print(f"Variación de venta en el período: "
                  f"{formato_importe(variacion)} ({porcentaje:+.2f}%)")
