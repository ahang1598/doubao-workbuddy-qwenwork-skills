"""Document conversion adapters package (soffice only)."""

from .soffice_adapter import SofficeAdapter
from .office_com_adapter import OfficeComAdapter

__all__ = [
    'OfficeComAdapter',
    'SofficeAdapter',
]
