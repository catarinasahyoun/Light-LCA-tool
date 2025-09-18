"""Report utilities and common functions."""

from typing import List
import docxtpl
import logging

logger = logging.getLogger(__name__)

# Import path constants
from ..config.paths import TEMPLATE


def _get_rows_for_report(selected_materials: List[str], materials_dict: dict, material_masses: dict, lifetime_years: float) -> List[dict]:
    """Generate material rows for report tables."""
    rows = []
    for m in selected_materials:
        props = materials_dict.get(m, {})
        mass = float(material_masses.get(m, 0.0))
        co2_per_kg = float(props.get("CO₂e (kg)", 0.0))
        co2_total = mass * co2_per_kg
        trees_mat = (co2_total / (22.0 * max(lifetime_years, 1e-9))) if lifetime_years else 0.0
        rows.append(
            {
                'MATERIAL': m,
                'CO2_TOTAL': f"{co2_total:.2f}",
                'RECYCLED_CONTENT': f"{float(props.get('Recycled Content', 0.0)):.0f}%",
                'CIRCULARITY': str(props.get("Circularity", "Unknown")),
                'EOL': str(props.get("EoL", "Unknown")),
                'TREES_MATERIAL': f"{trees_mat:.1f}"
            })
    return rows

def build_docx_from_template(project: str, notes: str, R: dict,
                            selected_materials: List[str], materials_dict: dict, material_masses: dict) -> docxtpl.DocxTemplate:
    """Build DOCX report from template using original app's logic."""
    print("Generating PDF report...")
    print(f"  Project: {project}")
    print(f"  Notes length: {len(notes) if notes else 0}")
    print(f"  Summary keys: {list(R.keys())}")
    print(f"  Selected materials: {selected_materials}")
    print(f"  Materials dict keys: {list(materials_dict.keys())[:5]}")
    print(f"  Material masses: {material_masses}")
    try:
        template = docxtpl.DocxTemplate(TEMPLATE)
        mapping = {
            "PROJECT": project,
            "LIFETIME_YEARS": f"{R['lifetime_years']:.1f}",
            "LIFETIME_WEEKS": f"{int(R['lifetime_years']*52)}",
            "TOTAL_CO2": f"{R['overall_co2']:.1f}",
            "WEIGHTED_RECYCLED": f"{R['weighted_recycled']:.1f}%",
            "TREES_YEAR": f"{R['trees_equiv']:.1f}",
            "TREES_TOTAL": f"{R['total_trees_equiv']:.1f}",
            "EXEC_NOTES": (notes or "").strip(),
            "materials": _get_rows_for_report(selected_materials, materials_dict, material_masses, R["lifetime_years"]) 
        }
        template.render(mapping)
        return template 
        
    except Exception as e:
        logger.exception("DOCX-from-template build failed")
        logger.error(f"Template load error: {e}")
        return None        
        