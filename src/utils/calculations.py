"""LCA calculation utilities."""

import streamlit as st
import re
from decimal import Decimal
from typing import Dict, List, Tuple


def extract_number(v):
    """Extract numeric value from a string or return the value if already numeric."""
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        s = s.replace('\u2212','-')   # minus sign → hyphen
        s = s.replace(',', '.')       # European decimals
        m = re.search(r"[-+]?\d*\.?\d+(e[-+]?\d+)?", s, flags=re.I)
        if not m:
            return 0.0
        return float(Decimal(m.group()))
    except Exception:
        return 0.0


def compute_results():
    """Compute results using the original app's logic."""
    data = st.session_state.assessment
    mats = st.session_state.materials
    total_material = 0.0
    total_process  = 0.0
    total_mass     = 0.0
    weighted       = 0.0
    eol            = {}
    cmp_rows       = []
    circ_map = {"high": 3, "medium": 2, "low": 1, "not circular": 0}
    
    for name in data.get('selected_materials', []):
        m = mats.get(name, {})
        mass = float(data.get('material_masses', {}).get(name, 0))
        total_mass += mass
        total_material += mass * float(m.get('CO₂e (kg)', 0))
        weighted += mass * float(m.get('Recycled Content', 0))
        eol[name] = m.get('EoL', 'Unknown')
        
        for s in data.get('processing_data', {}).get(name, []):
            total_process += float(s.get('amount', 0)) * float(s.get('co2e_per_unit', 0))
        
        cmp_rows.append({
            'Material': name,
            'CO2e per kg': float(m.get('CO₂e (kg)', 0)),
            'Recycled Content (%)': float(m.get('Recycled Content', 0)),
            'Circularity (mapped)': circ_map.get(str(m.get('Circularity','')).strip().lower(), 0),
            'Circularity (text)': m.get('Circularity', 'Unknown'),
            'Lifetime (years)': extract_number(m.get('Lifetime', 0)),
            'Lifetime (text)': m.get('Lifetime', 'Unknown'),
        })
    
    overall = total_material + total_process
    years = max(data.get('lifetime_weeks', 52) / 52, 1e-9)
    
    return {
        'total_material_co2': total_material,
        'total_process_co2': total_process,
        'overall_co2': overall,
        'weighted_recycled': (weighted / total_mass if total_mass > 0 else 0.0),
        'trees_equiv': overall / (22 * years),
        'total_trees_equiv': overall / 22,
        'lifetime_years': years,
        'eol_summary': eol,
        'comparison': cmp_rows
    }


class LCACalculator:
    """Calculator for LCA metrics and results."""
    
    @staticmethod
    def compute_results(assessment_data: dict, materials_dict: dict) -> dict:
        """Compute comprehensive LCA results from assessment data."""
        total_material = 0.0
        total_process = 0.0
        total_mass = 0.0
        weighted_recycled = 0.0
        eol_breakdown = {}
        comparison_rows = []
        
        # Circularity mapping
        circularity_map = {"high": 3, "medium": 2, "low": 1, "not circular": 0}
        
        for material_name in assessment_data.get('selected_materials', []):
            if material_name not in materials_dict:
                continue
            
            material_props = materials_dict[material_name]
            mass = assessment_data.get('material_masses', {}).get(material_name, 0.0)
            
            if mass <= 0:
                continue
            
            # Material carbon footprint
            co2e_per_kg = material_props.get('CO₂e (kg)', 0.0)
            material_co2e = mass * co2e_per_kg
            total_material += material_co2e
            
            # Process carbon footprint
            process_co2e = 0.0
            processing_steps = assessment_data.get('processing_data', {}).get(material_name, [])
            for step in processing_steps:
                if isinstance(step, dict) and step.get('process'):
                    amount = step.get('amount', 0.0)
                    co2e_per_unit = step.get('co2e_per_unit', 0.0)
                    process_co2e += amount * co2e_per_unit
            
            total_process += process_co2e
            
            # Mass and recycled content
            total_mass += mass
            recycled_pct = material_props.get('Recycled Content', 0.0) / 100.0
            weighted_recycled += mass * recycled_pct
            
            # End of life
            eol = material_props.get('EoL', 'Unknown')
            eol_breakdown[eol] = eol_breakdown.get(eol, 0.0) + mass
            
            # Comparison data
            comparison_rows.append({
                'Material': material_name,
                'Mass (kg)': mass,
                'Material CO₂e': material_co2e,
                'Process CO₂e': process_co2e,
                'Total CO₂e': material_co2e + process_co2e,
                'Recycled Content (%)': material_props.get('Recycled Content', 0.0),
                'EoL': eol,
                'Circularity': material_props.get('Circularity', 'Unknown')
            })
        
        # Calculate final metrics
        total_co2e = total_material + total_process
        recycled_content_pct = (weighted_recycled / total_mass * 100) if total_mass > 0 else 0.0
        lifetime_weeks = assessment_data.get('lifetime_weeks', 52)
        lifetime_years = lifetime_weeks / 52.0
        
        # Tree equivalent (rough calculation: 1 tree absorbs ~22kg CO2/year)
        trees_equivalent = total_co2e / (22 * lifetime_years) if lifetime_years > 0 else 0
        
        return {
            'total_co2e': total_co2e,
            'material_co2e': total_material,
            'process_co2e': total_process,
            'total_mass': total_mass,
            'recycled_content_pct': recycled_content_pct,
            'lifetime_weeks': lifetime_weeks,
            'lifetime_years': lifetime_years,
            'trees_equivalent': trees_equivalent,
            'eol_breakdown': eol_breakdown,
            'comparison_data': comparison_rows
        }