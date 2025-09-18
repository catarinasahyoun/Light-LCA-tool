"""PDF report generator using ReportLab."""

from .report_utils import build_docx_from_template
import tempfile
from io import BytesIO
import os
import subprocess
from docx2pdf import convert

def generate_pdf_report(project: str, notes: str, R: dict,
                            selected_materials: list, materials_dict: dict, material_masses: dict) -> bytes:
    """Generate PDF report."""
    filled_template = build_docx_from_template(project, notes, R, selected_materials, materials_dict, material_masses)
    with tempfile.NamedTemporaryFile(suffix=".docx") as tmp_docx:
        filled_template.save(tmp_docx.name)
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_tmp:
                    convert(tmp_docx.name, pdf_tmp.name)
                    pdf_tmp.seek(0)
                    return pdf_tmp.getvalue()
        except NotImplementedError:
            tmp_dir = tempfile.mkdtemp()
            result = subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp_dir, tmp_docx.name], capture_output=True, check=True, text=True, timeout=30)
            pdf_name = os.path.splitext(os.path.basename(tmp_docx.name))[0] + '.pdf'
            pdf_path = os.path.join(tmp_dir, pdf_name)
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            os.remove(pdf_path)
            os.rmdir(tmp_dir)
            return pdf_bytes
