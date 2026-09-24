"""Entidades del dominio de Book Manager (Sprint 1).

Cada clase representa una tabla del sistema. Los datos se guardan en
atributos privados y se exponen mediante propiedades que validan cada
valor antes de asignarlo (encapsulamiento). Todas las entidades saben
convertirse a un diccionario de cadenas y reconstruirse a partir de él,
que es el formato que utilizan los repositorios CSV para persistirlas.
"""
from __future__ import annotations

import abc
import datetime
from typing import ClassVar, Dict, Optional, Tuple, Type, TypeVar, Union

S = TypeVar("S", bound="Serializable")

ANIO_MINIMO = 1450
LONGITUDES_ISBN = (10, 13)
FORMATO_FECHA = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Funciones de validación reutilizadas por las propiedades de las entidades
# ---------------------------------------------------------------------------

def texto_obligatorio(valor: object, campo: str) -> str:
    """Devuelve el texto sin espacios sobrantes; falla si está vacío."""
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        raise ValueError(f"El campo '{campo}' no puede estar vacío.")
    return texto


def texto_opcional(valor: object) -> str:
    """Devuelve el texto sin espacios sobrantes o cadena vacía."""
    return "" if valor is None else str(valor).strip()


def entero_positivo(valor: object, campo: str) -> int:
    """Convierte el valor a entero mayor que cero o lanza ValueError."""
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"El campo '{campo}' debe ser un número entero.") from error
    if numero <= 0:
        raise ValueError(f"El campo '{campo}' debe ser mayor que cero.")
    return numero


def entero_no_negativo(valor: object, campo: str) -> int:
    """Convierte el valor a entero mayor o igual a cero o lanza ValueError."""
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"El campo '{campo}' debe ser un número entero.") from error
    if numero < 0:
        raise ValueError(f"El campo '{campo}' no puede ser negativo.")
    return numero


def numero_positivo(valor: object, campo: str) -> float:
    """Convierte el valor a un número decimal mayor que cero."""
    try:
        numero = float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{campo}' debe ser numérico.") from error
    if numero <= 0:
        raise ValueError(f"El campo '{campo}' debe ser mayor que cero.")
    return round(numero, 2)


def id_opcional(valor: object) -> Optional[int]:
    """Convierte un valor (posiblemente vacío) en un id entero o en None."""
    if valor is None or str(valor).strip() == "":
        return None
    return entero_positivo(valor, "id")


def fecha_desde(valor: object) -> datetime.date:
    """Acepta un date, un datetime o un texto 'AAAA-MM-DD' y devuelve date."""
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    try:
        return datetime.datetime.strptime(
            str(valor).strip(), FORMATO_FECHA).date()
    except ValueError as error:
        raise ValueError(
            "La fecha debe tener el formato AAAA-MM-DD.") from error


# ---------------------------------------------------------------------------
# Clases base
# ---------------------------------------------------------------------------

class Serializable(abc.ABC):
    """Contrato mínimo para que una entidad pueda persistirse en CSV."""

    #: Nombres y orden de las columnas con las que se persiste la entidad.
    CAMPOS: ClassVar[Tuple[str, ...]] = ()

    @abc.abstractmethod
    def a_dict(self) -> Dict[str, str]:
        """Devuelve la entidad como diccionario de cadenas (una fila CSV)."""

    @classmethod
    @abc.abstractmethod
    def desde_dict(cls: Type[S], datos: Dict[str, str]) -> S:
        """Construye la entidad a partir de una fila CSV."""

    def __repr__(self) -> str:
        campos = ", ".join(f"{k}={v!r}" for k, v in self.a_dict().items())
        return f"{type(self).__name__}({campos})"


class EntidadBase(Serializable):
    """Entidad identificada por un id numérico autoincremental."""

    CAMPOS: ClassVar[Tuple[str, ...]] = ("id",)

    def __init__(self, id: Optional[int] = None) -> None:
        self._id: Optional[int] = None
        self.id = id

    @property
    def id(self) -> Optional[int]:
        """Identificador único; None mientras la entidad no fue persistida."""
        return self._id

    @id.setter
    def id(self, valor: Optional[int]) -> None:
        self._id = id_opcional(valor)

    def _id_como_texto(self) -> str:
        return "" if self._id is None else str(self._id)


# ---------------------------------------------------------------------------
# Entidades de catálogo
# ---------------------------------------------------------------------------

class Genero(EntidadBase):
    """Categoría literaria a la que pertenece un libro."""

    CAMPOS = ("id", "nombre", "descripcion")

    def __init__(self, nombre: str, descripcion: str = "",
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._nombre = ""
        self._descripcion = ""
        self.nombre = nombre
        self.descripcion = descripcion

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = texto_obligatorio(valor, "nombre")

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor: str) -> None:
        self._descripcion = texto_opcional(valor)

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "nombre": self.nombre,
                "descripcion": self.descripcion}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Genero":
        return cls(nombre=datos["nombre"],
                   descripcion=datos.get("descripcion", ""),
                   id=id_opcional(datos.get("id")))

    def __str__(self) -> str:
        return self.nombre


class Editorial(EntidadBase):
    """Proveedor o distribuidora que provee los libros a la librería."""

    CAMPOS = ("id", "nombre", "pais")

    def __init__(self, nombre: str, pais: str = "",
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._nombre = ""
        self._pais = ""
        self.nombre = nombre
        self.pais = pais

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = texto_obligatorio(valor, "nombre")

    @property
    def pais(self) -> str:
        return self._pais

    @pais.setter
    def pais(self, valor: str) -> None:
        self._pais = texto_opcional(valor)

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "nombre": self.nombre,
                "pais": self.pais}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Editorial":
        return cls(nombre=datos["nombre"], pais=datos.get("pais", ""),
                   id=id_opcional(datos.get("id")))

    def __str__(self) -> str:
        return self.nombre


class Moneda(EntidadBase):
    """Moneda en la que puede expresarse un precio (ARS, USD, etc.)."""

    CAMPOS = ("id", "codigo", "nombre", "simbolo")

    def __init__(self, codigo: str, nombre: str, simbolo: str = "",
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._codigo = ""
        self._nombre = ""
        self._simbolo = ""
        self.codigo = codigo
        self.nombre = nombre
        self.simbolo = simbolo

    @property
    def codigo(self) -> str:
        """Código ISO 4217 de tres letras, siempre en mayúsculas."""
        return self._codigo

    @codigo.setter
    def codigo(self, valor: str) -> None:
        codigo = texto_obligatorio(valor, "codigo").upper()
        if len(codigo) != 3 or not codigo.isalpha():
            raise ValueError("El código de moneda debe tener 3 letras.")
        self._codigo = codigo

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = texto_obligatorio(valor, "nombre")

    @property
    def simbolo(self) -> str:
        return self._simbolo

    @simbolo.setter
    def simbolo(self, valor: str) -> None:
        self._simbolo = texto_opcional(valor)

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "codigo": self.codigo,
                "nombre": self.nombre, "simbolo": self.simbolo}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Moneda":
        return cls(codigo=datos["codigo"], nombre=datos["nombre"],
                   simbolo=datos.get("simbolo", ""),
                   id=id_opcional(datos.get("id")))

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class TipoCotizacion(EntidadBase):
    """Tipo de cotización del dólar (Oficial, Blue, MEP, etc.)."""

    CAMPOS = ("id", "nombre", "descripcion")

    def __init__(self, nombre: str, descripcion: str = "",
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._nombre = ""
        self._descripcion = ""
        self.nombre = nombre
        self.descripcion = descripcion

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = texto_obligatorio(valor, "nombre")

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor: str) -> None:
        self._descripcion = texto_opcional(valor)

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "nombre": self.nombre,
                "descripcion": self.descripcion}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "TipoCotizacion":
        return cls(nombre=datos["nombre"],
                   descripcion=datos.get("descripcion", ""),
                   id=id_opcional(datos.get("id")))

    def __str__(self) -> str:
        return self.nombre


class Libro(EntidadBase):
    """Título del catálogo. Se relaciona con Editorial y Genero por id."""

    CAMPOS = ("id", "isbn", "titulo", "autor", "editorial_id", "genero_id",
              "anio")

    def __init__(self, isbn: str, titulo: str, autor: str,
                 editorial_id: int, genero_id: int, anio: int,
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._isbn = ""
        self._titulo = ""
        self._autor = ""
        self._editorial_id = 0
        self._genero_id = 0
        self._anio = 0
        self.isbn = isbn
        self.titulo = titulo
        self.autor = autor
        self.editorial_id = editorial_id
        self.genero_id = genero_id
        self.anio = anio

    @property
    def isbn(self) -> str:
        """ISBN de 10 o 13 dígitos, sin guiones ni espacios."""
        return self._isbn

    @isbn.setter
    def isbn(self, valor: str) -> None:
        isbn = texto_obligatorio(valor, "isbn").replace("-", "")
        isbn = isbn.replace(" ", "")
        if not isbn.isdigit() or len(isbn) not in LONGITUDES_ISBN:
            raise ValueError("El ISBN debe tener 10 o 13 dígitos.")
        self._isbn = isbn

    @property
    def titulo(self) -> str:
        return self._titulo

    @titulo.setter
    def titulo(self, valor: str) -> None:
        self._titulo = texto_obligatorio(valor, "titulo")

    @property
    def autor(self) -> str:
        return self._autor

    @autor.setter
    def autor(self, valor: str) -> None:
        self._autor = texto_obligatorio(valor, "autor")

    @property
    def editorial_id(self) -> int:
        return self._editorial_id

    @editorial_id.setter
    def editorial_id(self, valor: int) -> None:
        self._editorial_id = entero_positivo(valor, "editorial_id")

    @property
    def genero_id(self) -> int:
        return self._genero_id

    @genero_id.setter
    def genero_id(self, valor: int) -> None:
        self._genero_id = entero_positivo(valor, "genero_id")

    @property
    def anio(self) -> int:
        """Año de publicación (entre 1450 y el año próximo)."""
        return self._anio

    @anio.setter
    def anio(self, valor: int) -> None:
        anio = entero_positivo(valor, "anio")
        anio_maximo = datetime.date.today().year + 1
        if not ANIO_MINIMO <= anio <= anio_maximo:
            raise ValueError(
                f"El año debe estar entre {ANIO_MINIMO} y {anio_maximo}.")
        self._anio = anio

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "isbn": self.isbn,
                "titulo": self.titulo, "autor": self.autor,
                "editorial_id": str(self.editorial_id),
                "genero_id": str(self.genero_id), "anio": str(self.anio)}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Libro":
        return cls(isbn=datos["isbn"], titulo=datos["titulo"],
                   autor=datos["autor"],
                   editorial_id=int(datos["editorial_id"]),
                   genero_id=int(datos["genero_id"]),
                   anio=int(datos["anio"]),
                   id=id_opcional(datos.get("id")))

    def __str__(self) -> str:
        return f"{self.titulo} ({self.autor})"


# ---------------------------------------------------------------------------
# Entidades de valuación
# ---------------------------------------------------------------------------

class Precio(EntidadBase):
    """Valor monetario de un libro en una moneda determinada."""

    CAMPOS = ("id", "libro_id", "moneda_id", "valor")

    def __init__(self, libro_id: int, moneda_id: int, valor: float,
                 id: Optional[int] = None) -> None:
        super().__init__(id)
        self._libro_id = 0
        self._moneda_id = 0
        self._valor = 0.0
        self.libro_id = libro_id
        self.moneda_id = moneda_id
        self.valor = valor

    @property
    def libro_id(self) -> int:
        return self._libro_id

    @libro_id.setter
    def libro_id(self, valor: int) -> None:
        self._libro_id = entero_positivo(valor, "libro_id")

    @property
    def moneda_id(self) -> int:
        return self._moneda_id

    @moneda_id.setter
    def moneda_id(self, valor: int) -> None:
        self._moneda_id = entero_positivo(valor, "moneda_id")

    @property
    def valor(self) -> float:
        """Importe con dos decimales, siempre mayor que cero."""
        return self._valor

    @valor.setter
    def valor(self, valor: float) -> None:
        self._valor = numero_positivo(valor, "valor")

    def a_dict(self) -> Dict[str, str]:
        return {"id": self._id_como_texto(), "libro_id": str(self.libro_id),
                "moneda_id": str(self.moneda_id),
                "valor": f"{self.valor:.2f}"}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Precio":
        return cls(libro_id=int(datos["libro_id"]),
                   moneda_id=int(datos["moneda_id"]),
                   valor=float(datos["valor"]),
                   id=id_opcional(datos.get("id")))


class Stock(Serializable):
    """Cantidad disponible de un libro. Su clave es el id del libro."""

    CAMPOS = ("libro_id", "cantidad", "cantidad_minima")

    def __init__(self, libro_id: int, cantidad: int = 0,
                 cantidad_minima: int = 0) -> None:
        self._libro_id = 0
        self._cantidad = 0
        self._cantidad_minima = 0
        self.libro_id = libro_id
        self.cantidad = cantidad
        self.cantidad_minima = cantidad_minima

    @property
    def libro_id(self) -> int:
        return self._libro_id

    @libro_id.setter
    def libro_id(self, valor: int) -> None:
        self._libro_id = entero_positivo(valor, "libro_id")

    @property
    def cantidad(self) -> int:
        return self._cantidad

    @cantidad.setter
    def cantidad(self, valor: int) -> None:
        self._cantidad = entero_no_negativo(valor, "cantidad")

    @property
    def cantidad_minima(self) -> int:
        """Umbral por debajo del cual se considera stock bajo."""
        return self._cantidad_minima

    @cantidad_minima.setter
    def cantidad_minima(self, valor: int) -> None:
        self._cantidad_minima = entero_no_negativo(valor, "cantidad_minima")

    def esta_bajo_minimo(self) -> bool:
        """Indica si la cantidad disponible es menor al mínimo definido."""
        return self.cantidad < self.cantidad_minima

    def ingresar(self, unidades: int) -> None:
        """Suma unidades al stock (por ejemplo, ante una compra)."""
        self.cantidad += entero_positivo(unidades, "unidades")

    def egresar(self, unidades: int) -> None:
        """Descuenta unidades del stock; falla si no hay suficientes."""
        unidades = entero_positivo(unidades, "unidades")
        if unidades > self.cantidad:
            raise ValueError(
                f"Stock insuficiente: hay {self.cantidad} unidades.")
        self.cantidad -= unidades

    def a_dict(self) -> Dict[str, str]:
        return {"libro_id": str(self.libro_id),
                "cantidad": str(self.cantidad),
                "cantidad_minima": str(self.cantidad_minima)}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "Stock":
        return cls(libro_id=int(datos["libro_id"]),
                   cantidad=int(datos["cantidad"]),
                   cantidad_minima=int(datos.get("cantidad_minima", 0)))


class CotizacionDolar(Serializable):
    """Cotización histórica del dólar. Su clave es (tipo_id, fecha)."""

    CAMPOS = ("tipo_id", "fecha", "compra", "venta")

    def __init__(self, tipo_id: int, fecha: Union[datetime.date, str],
                 compra: float, venta: float) -> None:
        self._tipo_id = 0
        self._fecha = datetime.date.today()
        self._compra = 0.0
        self._venta = 0.0
        self.tipo_id = tipo_id
        self.fecha = fecha
        self.compra = compra
        self.venta = venta

    @property
    def tipo_id(self) -> int:
        return self._tipo_id

    @tipo_id.setter
    def tipo_id(self, valor: int) -> None:
        self._tipo_id = entero_positivo(valor, "tipo_id")

    @property
    def fecha(self) -> datetime.date:
        return self._fecha

    @fecha.setter
    def fecha(self, valor: Union[datetime.date, str]) -> None:
        self._fecha = fecha_desde(valor)

    @property
    def compra(self) -> float:
        return self._compra

    @compra.setter
    def compra(self, valor: float) -> None:
        self._compra = numero_positivo(valor, "compra")

    @property
    def venta(self) -> float:
        return self._venta

    @venta.setter
    def venta(self, valor: float) -> None:
        self._venta = numero_positivo(valor, "venta")

    @property
    def promedio(self) -> float:
        """Promedio entre compra y venta."""
        return round((self.compra + self.venta) / 2, 2)

    def a_dict(self) -> Dict[str, str]:
        return {"tipo_id": str(self.tipo_id),
                "fecha": self.fecha.strftime(FORMATO_FECHA),
                "compra": f"{self.compra:.2f}", "venta": f"{self.venta:.2f}"}

    @classmethod
    def desde_dict(cls, datos: Dict[str, str]) -> "CotizacionDolar":
        return cls(tipo_id=int(datos["tipo_id"]), fecha=datos["fecha"],
                   compra=float(datos["compra"]),
                   venta=float(datos["venta"]))
