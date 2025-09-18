# Database Module

## 📋 Overview

The database module (`src/database/`) handles all data persistence and Excel file operations for the TCHAI LCA Tool. It provides a robust system for managing LCA material databases, parsing Excel files, and maintaining data integrity throughout the application lifecycle.

## 🏗️ Architecture

```
database/
├── __init__.py          # Module exports and database manager
├── db_manager.py        # Core database management and operations
├── excel_utils.py       # Excel file parsing and validation utilities
└── parsers.py          # Data parsing and transformation logic
```

## 🔧 Components

### 1. **Database Manager** ([`database_manager.py`](database_manager.py))
**Purpose**: Core database operations and Excel file management

**Key Responsibilities**:
- Excel file loading and validation
- Data structure management and consistency
- Active database tracking and switching
- Backup and recovery operations

**Key Methods**:
- `load_database()`: Load and validate Excel database
- `get_active_database()`: Retrieve current database configuration
- `set_active_database()`: Switch to different database version
- `validate_database_structure()`: Ensure data integrity

**Integration Points**:
- **Config**: Uses database paths from [`../config/README.md`](../config/README.md)
- **Models**: Returns data in structured models via [`../models/README.md`](../models/README.md)
- **Used by**: [`../pages/README.md`](../pages/README.md) for data access

### 2. **Excel Handler** ([`excel_handler.py`](excel_handler.py))
**Purpose**: Low-level Excel file operations and data extraction

**Key Responsibilities**:
- Excel file reading with pandas integration
- Sheet validation and structure checking
- Data cleaning and preprocessing
- Column mapping and data type enforcement

**Features**:
- **Multi-sheet support**: Handle complex Excel workbooks
- **Error resilience**: Graceful handling of malformed data
- **Data validation**: Type checking and constraint enforcement
- **Memory efficient**: Optimized pandas operations

**Integration Points**:
- **Used by**: [`database_manager.py`](database_manager.py) for file operations
- **Config**: Uses file paths from [`../config/README.md`](../config/README.md)
- **Models**: Converts data to structured models via [`../models/README.md`](../models/README.md)

### 3. **Data Parsers** (`parsers.py`)
**Purpose**: Transform raw Excel data into structured application data

**Key Responsibilities**:
- Convert Excel rows to material/process objects
- Data normalization and standardization
- Unit conversion and validation
- Missing data handling and defaults
- Data relationship mapping

**Parser Types**:

#### **Material Parser**
```python
def parse_materials(df: pd.DataFrame) -> Dict[str, Material]:
    """Parse Excel data into Material objects"""
    # Convert rows to Material instances
    # Validate required fields
    # Apply data transformations
    # Handle missing/invalid data
```

#### **Process Parser**
```python
def parse_processes(df: pd.DataFrame) -> Dict[str, Process]:
    """Parse Excel data into Process objects"""
    # Convert rows to Process instances
    # Validate process parameters
    # Link to material dependencies
    # Calculate derived values
```

#### **Database Metadata Parser**
```python
def parse_database_metadata(df: pd.DataFrame) -> DatabaseInfo:
    """Extract database version and metadata"""
    # Parse version information
    # Extract creation/modification dates
    # Validate database compatibility
```

## 🗃️ Database Structure

### **Excel File Format**
The application expects Excel files with specific sheet structure:

#### **Materials Sheet**
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| Name | str | Material name/identifier | ✅ |
| CO₂e (kg) | float | Carbon footprint per kg | ✅ |
| Recycled Content | float | Percentage recycled content | ✅ |
| Circularity | str | Circularity rating (high/medium/low) | ✅ |
| EoL | str | End-of-life treatment | ✅ |
| Lifetime | str | Expected lifetime | ✅ |
| Category | str | Material category | ❌ |
| Description | str | Detailed description | ❌ |

#### **Processes Sheet**
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| Name | str | Process name/identifier | ✅ |
| CO₂e per unit | float | Carbon footprint per unit | ✅ |
| Unit | str | Process unit (kg, m², etc.) | ✅ |
| Category | str | Process category | ❌ |
| Description | str | Process description | ❌ |

### **Active Database Configuration**
```json
{
  "active_database": "database_latest.xlsx",
  "last_updated": "2025-09-17T14:30:00Z",
  "version": "2.1",
  "metadata": {
    "materials_count": 150,
    "processes_count": 75,
    "last_validation": "2025-09-17T14:30:00Z"
  }
}
```

## 🔄 Data Flow

### 1. **Database Loading Process**
```
Database Request
├── Check active database configuration
├── Load Excel file from disk
├── Validate file structure and format
├── Parse materials and processes
├── Apply data transformations
├── Cache parsed data in memory
└── Return structured data objects
```

### 2. **Data Access Pattern**
```
Application Data Request
├── DatabaseManager.get_materials()
├── Check in-memory cache first
├── Load from Excel if not cached
├── Validate data integrity
├── Apply filters if requested
└── Return material/process data
```

### 3. **Database Switching**
```
User Selects New Database
├── Validate new Excel file
├── Parse and cache new data
├── Update active database config
├── Clear old cache entries
├── Notify dependent components
└── Update UI with new data
```

## 📊 Data Management Features

### 1. **Caching Strategy**
- **In-Memory Cache**: Parsed data stored in memory for fast access
- **Cache Invalidation**: Automatic refresh when Excel files change
- **Lazy Loading**: Data loaded only when requested
- **Memory Management**: Configurable cache size limits

### 2. **Data Validation**
- **Schema Validation**: Ensure required columns exist
- **Data Type Checking**: Validate numeric fields and formats
- **Range Validation**: Check values are within expected ranges
- **Consistency Checks**: Cross-validate related data fields

### 3. **Error Recovery**
- **Graceful Degradation**: Continue with partial data if possible
- **Default Values**: Provide sensible defaults for missing data
- **Error Reporting**: Detailed error messages for troubleshooting
- **Backup Systems**: Fallback to previous known-good database

## 🚀 Usage Examples

### **Basic Database Operations**
```python
from src.database import DatabaseManager

# Initialize database manager
db = DatabaseManager()

# Load and access materials
materials = db.get_materials()
material = materials.get('Steel')

# Access processes
processes = db.get_processes()
process = processes.get('Manufacturing')

# Switch active database
success = db.set_active_database('new_database.xlsx')
```

### **Excel File Operations**
```python
from src.database.excel_utils import load_excel_file, validate_excel_structure

# Load Excel file
df = load_excel_file(Path('database.xlsx'))

# Validate structure
is_valid = validate_excel_structure(df)
if not is_valid:
    print("Invalid Excel file structure")
```

### **Data Parsing**
```python
from src.database.parsers import parse_materials, parse_processes

# Parse Excel data
materials_df = pd.read_excel('database.xlsx', sheet_name='Materials')
materials = parse_materials(materials_df)

processes_df = pd.read_excel('database.xlsx', sheet_name='Processes')  
processes = parse_processes(processes_df)
```

## 🔧 Configuration

### **Database Paths**
- Primary database location: `assets/databases/`
- Active database config: `assets/databases/active.json`
- Backup databases: `assets/databases/backups/`

### **Supported Formats**
- Excel formats: `.xlsx`, `.xls`
- Sheet naming conventions: `Materials`, `Processes`, `Metadata`
- Character encoding: UTF-8, Windows-1252

### **Performance Settings**
```python
# Cache configuration
CACHE_SIZE_LIMIT = 100  # MB
CACHE_TTL = 3600       # seconds
LAZY_LOADING = True    # Load data on demand

# Excel parsing settings
MAX_ROWS = 10000       # Maximum rows to process
CHUNK_SIZE = 1000      # Rows per processing chunk
```

## 🛡️ Data Integrity

### **Validation Rules**
1. **Required Fields**: All essential columns must be present
2. **Data Types**: Numeric fields must contain valid numbers
3. **Value Ranges**: CO₂e values must be positive
4. **Consistency**: Related fields must be logically consistent
5. **Uniqueness**: Material/process names must be unique

### **Error Handling**
```python
class DatabaseError(Exception):
    """Base exception for database operations"""

class InvalidExcelFormatError(DatabaseError):
    """Excel file format is invalid"""

class MissingDataError(DatabaseError):
    """Required data is missing"""

class DataValidationError(DatabaseError):
    """Data validation failed"""
```

### **Data Backup and Recovery**
- **Automatic Backups**: Previous database versions preserved
- **Rollback Capability**: Revert to previous known-good state
- **Change Tracking**: Log all database modifications
- **Integrity Checks**: Regular validation of database consistency

## 🔗 Integration Points

### **Upstream Dependencies**
- `config/paths.py`: File path configuration
- `models/`: Data model definitions
- `pandas`: Excel file operations
- `openpyxl`: Excel file reading/writing

### **Downstream Consumers**
- [`../pages/README.md`](../pages/README.md): Material selection and input
- [`../utils/README.md`](../utils/README.md): LCA calculation data
- [`../reports/README.md`](../reports/README.md): Data for report generation

## 📈 Performance Considerations

### **Memory Usage**
- Parsed data cached in memory for fast access
- Configurable cache size limits to prevent memory issues
- Lazy loading to minimize initial memory footprint

### **File I/O Optimization**
- Excel files read once and cached
- Incremental loading for large databases
- Background validation to avoid UI blocking

### **Scalability**
- Designed for databases with thousands of materials
- Efficient search and filtering algorithms
- Paginated data access for large datasets

## 🎯 Future Enhancements

1. **Database Versioning**: Track database schema changes
2. **SQL Backend**: Migration from Excel to proper database
3. **Real-time Sync**: Multi-user database synchronization
4. **Import/Export Tools**: Better data exchange capabilities
5. **Data Validation UI**: Interactive validation and correction
6. **Audit Trail**: Complete change history tracking
7. **Performance Monitoring**: Database operation metrics
8. **Automated Backups**: Scheduled backup operations