# Reports Module

## 📋 Overview

The reports module (`src/reports/`) handles PDF and DOCX report generation for LCA assessments. It provides multiple output formats with template-based generation and fallback options for different deployment scenarios.

## 🏗️ Architecture

```
reports/
├── __init__.py          # Report exports and factory functions
├── pdf_generator.py     # PDF report generation using ReportLab
├── docx_generator.py    # DOCX report generation using python-docx
└── report_utils.py      # Shared utilities and template helpers
```

## 🔧 Components

### 1. **PDF Generator** ([`pdf_generator.py`](pdf_generator.py))
**Purpose**: PDF report creation and formatting

**Key Responsibilities**:
- PDF document structure and layout
- Chart and graph embedding
- Table formatting and styling
- Multi-page document management

**Features**:
- **Custom styling**: Corporate branding and themes
- **Data visualization**: Charts, graphs, and infographics
- **Template-based**: Consistent formatting across reports
- **Print optimization**: High-quality printable output

**Integration Points**:
- **Utils**: Chart generation via [`../utils/README.md`](../utils/README.md)
- **Config**: Template paths via [`../config/README.md`](../config/README.md)
- **Models**: Data structures via [`../models/README.md`](../models/README.md)

### 2. **DOCX Generator** ([`docx_generator.py`](docx_generator.py))
**Purpose**: Microsoft Word document generation

**Key Responsibilities**:
- DOCX template processing
- Dynamic content insertion
- Table and image embedding
- Style and formatting preservation

**Features**:
- **Template merging**: Placeholder replacement in DOCX templates
- **Rich formatting**: Preserve styles, fonts, and layouts
- **Table automation**: Dynamic table generation with data
- **Cross-references**: Automatic figure and table numbering

**Integration Points**:
- **Config**: Template file paths via [`../config/README.md`](../config/README.md)
- **Utils**: Data processing via [`../utils/README.md`](../utils/README.md)
- **Models**: Structured data via [`../models/README.md`](../models/README.md)

### 3. **Report Generator** ([`report_generator.py`](report_generator.py))
**Purpose**: High-level report orchestration and management

**Key Responsibilities**:
- Report generation workflow coordination
- Multi-format output management
- Data aggregation and preparation
- Report validation and quality assurance

**Features**:
- **Multi-format support**: Automatic PDF and DOCX generation
- **Data pipeline**: LCA data processing and validation
- **Template management**: Dynamic template selection
- **Error handling**: Robust error recovery and reporting

**Integration Points**:
- **Uses**: [`pdf_generator.py`](pdf_generator.py) and [`docx_generator.py`](docx_generator.py)
- **Utils**: Calculation results via [`../utils/README.md`](../utils/README.md)
- **Database**: Source data via [`../database/README.md`](../database/README.md)
- **Pages**: UI integration via [`../pages/README.md`](../pages/README.md)

## 🔄 Report Generation Flow

```
Results Page Request
├── Collect assessment data
├── Format data for templates
├── Try DOCX template (preferred)
├── Fallback to PDF generation
├── Fallback to DOCX without template
├── Final fallback to plain text
└── Return downloadable file
```

## 📄 Report Formats

### **1. DOCX from Template**
- Uses existing Word template with placeholders
- Replaces `{TOKEN}` markers with live data
- Preserves template formatting and styling
- Best quality output when template available

### **2. PDF Report**
- Generated using ReportLab library
- Professional layout with tables and metrics
- Custom branding and styling
- Works without external templates

### **3. DOCX Fallback**
- Generated programmatically without template
- Basic formatting and structure
- Works when template not available

### **4. Plain Text**
- Simple text format with key metrics
- Ultimate fallback when libraries unavailable
- Ensures some output is always possible

## 🎨 Template System

### **Template Structure**
Templates use token replacement for dynamic content:

```
{PROJECT} — Easy LCA Report

Key Metrics:
- Total CO₂e: {TOTAL_CO2} kg
- Trees Equivalent: {TREES_EQUIV}
- Recycled Content: {RECYCLED_PERCENT}%

{MATERIAL_TABLE}

{EXECUTIVE_NOTES}
```

### **Supported Tokens**
- `{PROJECT}`: Project name
- `{TOTAL_CO2}`: Total carbon footprint
- `{TREES_EQUIV}`: Tree equivalent calculation
- `{RECYCLED_PERCENT}`: Weighted recycled content
- `{MATERIAL_TABLE}`: Formatted material data table
- `{EXECUTIVE_NOTES}`: User-provided notes

## 🚀 Usage Examples

### **Generate Report**
```python
from src.reports.pdf_generator import build_pdf_from_template

# Generate PDF report
pdf_bytes = build_pdf_from_template(
    project="My Project",
    notes="Executive summary...",
    summary=calculation_results,
    selected_materials=materials,
    materials_dict=material_database,
    material_masses=material_amounts
)

# Provide download
st.download_button(
    "Download PDF Report",
    data=pdf_bytes,
    file_name="report.pdf",
    mime="application/pdf"
)
```

## 🔗 Integration Points

### **Used By**
- [`../pages/README.md`](../pages/README.md): Report generation interface

### **Dependencies**
- [`../utils/README.md`](../utils/README.md): Template discovery and file operations
- [`../config/README.md`](../config/README.md): File path management
- `reportlab`: PDF generation
- `python-docx`: DOCX generation

### **Template Files**
- Report templates: `assets/guides/report_template_cleaned.docx`
- Logo files: `assets/tchai_logo.png`
- Font files: `assets/fonts/`