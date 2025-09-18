"""Reports module for generating PDF and DOCX reports."""

from .pdf_generator import generate_pdf_report
from .docx_generator import generate_docx_report
from .report_utils import build_docx_from_template