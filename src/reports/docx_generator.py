"""DOCX report generator using python-docx."""

from .report_utils import build_docx_from_template
from io import BytesIO

def generate_docx_report(project: str, notes: str, R: dict,
                         selected_materials: list, materials_dict: dict, material_masses: dict) -> bytes:
    """Generate DOCX report."""
    filled_template = build_docx_from_template(project, notes, R, selected_materials, materials_dict, material_masses)
    bio = BytesIO()
    filled_template.save(bio)
    return bio.getvalue()



