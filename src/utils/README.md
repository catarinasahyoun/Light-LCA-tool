# Utils Module

## 📋 Overview

The utils module (`src/utils/`) contains ### 3. **Version Management** ([`version_utils.py`](version_utils.py))
**Purpose**: Application version control and update management

**Key Functions**:
- `get_current_version()`: Application version detection
- `check_version_compatibility()`: Database version validation
- `create_version_backup()`: Version state preservation
- `migrate_version()`: Version upgrade handling

**Features**:
- **Semantic versioning**: Standard version numbering support
- **Compatibility checking**: Version conflict detection
- **Backup management**: Automatic version state preservation
- **Migration support**: Smooth version transitions

**Integration Points**:
- **Database**: Version tracking via [`../database/README.md`](../database/README.md)
- **Config**: Version constants via [`../config/README.md`](../config/README.md)
- **Used by**: [`../pages/README.md`](../pages/README.md) for version management UIons, business logic, and helper components that support the core functionality of the TCHAI LCA Tool. It includes LCA calculations, file operations, internationalization, and version management.

## 🏗️ Architecture

```
utils/
├── __init__.py          # Utility exports and common functions
├── calculations.py      # LCA calculations and algorithms
├── file_utils.py        # File operations and template handling
├── i18n.py             # Internationalization and language support
└── version_manager.py   # Assessment version management
```

## 🔧 Components

### 1. **Calculations Engine** ([`calculations.py`](calculations.py))
**Purpose**: Core LCA mathematical operations and carbon footprint calculations

**Key Functions**:
- `calculate_carbon_footprint()`: Material-based CO₂ calculations
- `compute_results()`: Comprehensive LCA assessment results
- `trees_equivalent()`: Environmental impact visualization
- `lifetime_impact()`: Long-term environmental assessment

**Features**:
- **Precision calculations**: High-accuracy floating-point operations
- **Unit conversions**: Automatic handling of measurement units
- **Data validation**: Input sanitization and range checking
- **Performance optimization**: Efficient algorithms for large datasets

**Integration Points**:
- **Database**: Material data access via [`../database/README.md`](../database/README.md)
- **Models**: Data structures via [`../models/README.md`](../models/README.md)
- **Used by**: [`../pages/README.md`](../pages/README.md) for real-time calculations

### 2. **File Utilities** ([`file_utils.py`](file_utils.py))
**Purpose**: File system operations and template management

**Key Functions**:
- `ensure_directory()`: Safe directory creation
- `backup_file()`: File backup and versioning
- `validate_file_type()`: File format validation

**Features**:
- **Cross-platform compatibility**: Works on Windows, macOS, Linux
- **Error handling**: Robust file operation error recovery
- **Permission management**: Safe file access with proper permissions
- **Template resolution**: Smart template file discovery

**Integration Points**:
- **Config**: File paths via [`../config/README.md`](../config/README.md)
- **Reports**: Template discovery via [`../reports/README.md`](../reports/README.md)
- **Used by**: Various modules for file operations

### 3. **Internationalization** (`i18n.py`)
**Purpose**: Multi-language support and localization

**Key Features**:
- Translation key management
- Dynamic language switching
- Fallback to default language
- Context-aware translations

**Core Classes**:
- `Translator`: Main translation manager
- Language file loading and caching
- Translation key validation

### 4. **String Processing** ([`string_utils.py`](string_utils.py))
**Purpose**: Text processing and data extraction utilities

**Key Functions**:
- `extract_number()`: Numeric value extraction from text
- `clean_material_name()`: Material name standardization
- `format_units()`: Unit formatting and display
- `sanitize_input()`: Input validation and cleaning

**Features**:
- **Regex processing**: Advanced pattern matching for data extraction
- **Input sanitization**: XSS prevention and data cleaning
- **Format standardization**: Consistent text formatting
- **Localization support**: Multi-language text processing

**Integration Points**:
- **Database**: Data cleaning via [`../database/README.md`](../database/README.md)
- **Models**: Input validation via [`../models/README.md`](../models/README.md)
- **UI**: Text formatting via [`../ui/README.md`](../ui/README.md)

## 🧮 LCA Calculation Engine

### **Core Calculation Flow**
```
Assessment Data Input
├── Material Impact Calculation
│   ├── Mass × CO₂e per kg
│   ├── Recycled content weighting
│   └── End-of-life treatment
├── Process Impact Calculation
│   ├── Process steps evaluation
│   ├── Amount × CO₂e per unit
│   └── Manufacturing impacts
├── Aggregation and Totals
│   ├── Total material CO₂e
│   ├── Total process CO₂e
│   └── Overall carbon footprint
└── Derived Metrics
    ├── Tree equivalents
    ├── Lifetime impacts
    └── Comparison data
```

### **Key Formulas**
```python
# Total carbon footprint
total_co2e = material_co2e + process_co2e

# Tree equivalent calculation
trees_per_year = total_co2e / (22 * lifetime_years)
total_trees = total_co2e / 22

# Weighted recycled content
weighted_recycled = sum(mass * recycled_pct) / total_mass
```

## 🔄 Version Management System

### **Version Data Structure**
```json
{
  "id": "uuid-string",
  "name": "Assessment Name",
  "created_at": "2025-09-17T14:30:00Z",
  "user": "user@example.com",
  "assessment_data": {
    "selected_materials": [...],
    "material_masses": {...},
    "processing_data": {...},
    "lifetime_weeks": 52
  },
  "metadata": {
    "description": "Optional description",
    "tags": ["tag1", "tag2"],
    "version": "1.0"
  }
}
```

### **Version Operations**
```python
# Save current assessment
version_id = VersionManager.save_version(
    name="Building Assessment v1",
    assessment_data=st.session_state.assessment,
    user_email="user@example.com"
)

# Load saved assessment
assessment = VersionManager.load_version(version_id)
st.session_state.assessment = assessment

# List all versions
versions = VersionManager.list_versions()
```

## 🌐 Internationalization System

### **Translation Key Structure**
```json
{
  "nav": {
    "tool": "Actual Tool",
    "results": "Results",
    "settings": "Settings"
  },
  "messages": {
    "welcome": "Welcome to TCHAI LCA Tool",
    "calculation_complete": "Calculation completed successfully"
  },
  "errors": {
    "file_not_found": "File not found",
    "invalid_data": "Invalid data format"
  }
}
```

### **Usage Pattern**
```python
from src.utils.i18n import Translator

# Get translation function
t = Translator.t

# Use translations with fallback
page_title = t("nav.tool", "Actual Tool")
error_msg = t("errors.invalid_data", "Invalid data")
```

## 🔧 File Utilities

### **Asset Loading**
```python
# Load logo for UI
logo_bytes = FileUtils.load_logo_bytes(LOGO_CANDIDATES)
logo_html = FileUtils.create_logo_tag(logo_bytes)

# Embed fonts in CSS
font_css = FileUtils.embed_font_css(FONTS_DIR)
st.markdown(f"<style>{font_css}</style>", unsafe_allow_html=True)

```

### **Template Discovery**
The system searches for templates in multiple locations:
1. Configured template candidates
2. Assets/guides directory
3. Fuzzy name matching for "report" + "template"
4. Validation of DOCX file integrity

## 🚀 Usage Examples

### **LCA Calculations**
```python
from src.utils.calculations import compute_results

# Compute results from session state
results = compute_results()

# Access calculated values
total_co2 = results['overall_co2']
trees_equiv = results['trees_equiv']
comparison_data = results['comparison']
```

### **Version Management**
```python
from src.utils.version_manager import VersionManager

# Save current work
version_id = VersionManager.save_version(
    name="My Assessment v1",
    assessment_data=st.session_state.assessment,
    user_email=current_user.email
)

# Load previous work  
saved_assessment = VersionManager.load_version(version_id)
st.session_state.assessment = saved_assessment
```

## 🔗 Integration Points

### **Used By**
- [`../pages/README.md`](../pages/README.md): All pages use utility functions
- [`../reports/README.md`](../reports/README.md): File utilities for template handling
- [`../../main.py`](../../main.py): Internationalization setup
- [`../database/README.md`](../database/README.md): Number extraction utilities

### **Dependencies**
- [`../config/README.md`](../config/README.md): Path configuration and settings
- [`../models/README.md`](../models/README.md): Data model validation
- `streamlit`: Session state access
- Standard Python libraries for calculations

## 📊 Performance Considerations

### **Calculation Optimization**
- Results cached in session state
- Incremental calculations where possible
- Efficient data structures for large datasets

### **File Operations**
- Template discovery cached
- Logo/font loading optimized with Base64 encoding
- Error handling prevents file system blocking

### **Version Management**
- JSON-based storage for fast read/write
- Metadata indexing for quick version listing
- Configurable storage limits

## 🎯 Future Enhancements

1. **Advanced Calculations**: More sophisticated LCA algorithms
2. **Caching System**: Better performance for repeated calculations
3. **Template Engine**: More flexible template system
4. **Version Comparison**: Side-by-side assessment comparison
5. **Export Formats**: Additional export options (CSV, JSON)
6. **Calculation Validation**: Automated result verification
7. **Plugin System**: Extensible calculation modules