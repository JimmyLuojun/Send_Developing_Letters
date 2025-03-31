# src/data_access/__init__.py
"""Package for accessing data from various sources (files, websites)."""

from .docx_reader import read_skyfend_business
from .excel_reader import read_company_data
from .website_scraper import fetch_website_content

__all__ = [
    "read_skyfend_business",
    "read_company_data",
    "fetch_website_content",
]