# Configuration Module

## 📋 Overview

The configuration module (`src/config/`) centralizes all application settings, path management, and system configuration for the TCHAI LCA Tool. It provides a single source of truth for application constants, file paths, and environment-specific settings.

## 🏗️ Architecture

```
config/
├── __init__.py          # Module exports and central configuration
├── logging_config.py    # Logging system configuration
├── paths.py            # File paths and directory management
└── settings.py         # Application constants and settings
```

## 🔧 Components

### 1. **Central Configuration** ([`__init__.py`](__init__.py))
**Purpose**: Aggregates all configuration elements and provides unified access

**Key Exports**:
- `PAGE_CONFIG`: Streamlit page configuration dictionary
- `setup_logging()`: Logging system initialization function
- Application-wide constants and settings

**Usage Pattern**:
```python
from src.config import PAGE_CONFIG, setup_logging
```

### 2. **Logging Configuration** ([`logging_config.py`](logging_config.py))
**Purpose**: Centralized logging setup and management

**Key Responsibilities**:
- Logger configuration and formatting
- Log file management and rotation
- Log level configuration for different environments
- Custom log formatters and handlers

**Features**:
- **File logging**: Persistent logs in `assets/logs/app.log`
- **Console logging**: Development-friendly console output
- **Log rotation**: Automatic log file management
- **Level filtering**: Configurable verbosity levels

**Interactions**:
- **Uses**: [`paths.py`](paths.py) for log file locations
- **Used by**: [`../../main.py`](../../main.py) for application startup
- **Used by**: All modules for logging operations

### 3. **Path Management** ([`paths.py`](paths.py))
**Purpose**: Centralized file path and directory structure management

**Key Responsibilities**:
- Asset directory paths (fonts, templates, guides)
- Database file paths (Excel files, active data)
- User data paths (authentication, logs)
- Template and output file management

**Features**:
- **Cross-platform paths**: Uses `pathlib` for OS compatibility
- **Relative path resolution**: Automatic path calculation from project root
- **Directory creation**: Ensures required directories exist
- **File validation**: Path existence and accessibility checks

**Directory Structure Management**:
```
assets/
├── databases/         # LCA data files
├── fonts/            # UI typography assets
├── guides/           # User documentation
├── i18n/             # Internationalization files
└── logs/             # Application logs
```

**Interactions**:
- **Used by**: All modules requiring file system access
- **Database module**: For Excel file paths via [`../database/README.md`](../database/README.md)
- **Reports module**: For template and output paths via [`../reports/README.md`](../reports/README.md)
- **UI module**: For asset paths via [`../ui/README.md`](../ui/README.md)

### 4. **Application Settings** (`settings.py`)
**Purpose**: Application constants, defaults, and configuration values

**Key Configuration Categories**:

#### **UI Settings**
```python
# Color scheme and theming
PRIMARY_COLOR = "#6366f1"     # Main brand color
BACKGROUND_COLOR = "#f8fafc"  # Background color
SUCCESS_COLOR = "#10b981"     # Success message color
ERROR_COLOR = "#ef4444"       # Error message color
```

#### **Authentication Settings**
```python
# Default user configuration
DEFAULT_USERS = ["admin@tchai.com"]
DEFAULT_PASSWORD = "admin123"
BCRYPT_ROUNDS = 12            # Password hashing complexity
```

#### **LCA Calculation Settings**
```python
# Calculation constants
TREE_CO2_ABSORPTION = 22     # kg CO₂ per tree per year
DEFAULT_LIFETIME_WEEKS = 52  # Default product lifetime
CARBON_INTENSITY_FACTORS = {...}  # Material carbon factors
```

#### **File Format Settings**
```python
# Supported file formats
EXCEL_EXTENSIONS = ['.xlsx', '.xls']
TEMPLATE_EXTENSIONS = ['.docx']
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg']
```

**Interactions**:
- **Used by**: All modules for consistent configuration
- **Environment-aware**: Can be modified for different deployments

## 🔄 Configuration Flow

### 1. **Application Startup**
```
main.py
├── Import config module
├── Load PAGE_CONFIG for Streamlit
├── Initialize logging system
├── Apply UI settings and theme
└── Bootstrap with default settings
```

### 2. **Path Resolution**
```
Module needs file access
├── Import from config.paths
├── Use predefined path constants
├── Automatic directory creation
├── Conflict resolution if needed
└── Return validated path
```

### 3. **Settings Access**
```
Module needs configuration
├── Import from config.settings
├── Access constant values
├── Apply environment overrides
└── Use configured values
```

## 📂 Key Path Constants

### **Base Directories**
- `APP_DIR`: Application root directory
- `ASSETS`: Main assets directory (`assets/`)
- `DB_ROOT`: Database files (`assets/databases/`)
- `GUIDES`: Documentation (`assets/guides/`)
- `FONTS`: Font files (`assets/fonts/`)
- `LOGS_DIR`: Log files (`assets/logs/`)
- `LANG_FILE_DIR`: i18n files (`assets/i18n/`)

### **Important Files**
- `USERS_FILE`: User database (`assets/users.json`)
- `ACTIVE_DB_FILE`: Active database config (`assets/databases/active.json`)

### **Resource Discovery**
- `LOGO_CANDIDATES`: List of possible logo file locations
- `TEMPLATE_CANDIDATES`: List of possible report template locations

## ⚙️ Configuration Patterns

### 1. **Environment-Based Configuration**
```python
# Development vs Production settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Database configuration
DB_PATH = os.getenv('DB_PATH', str(DB_ROOT / 'active.json'))
```

### 2. **Feature Flags**
```python
# Optional feature enablement
ENABLE_ADVANCED_FEATURES = True
ENABLE_EXPORT_FEATURES = True
ENABLE_VERSION_MANAGEMENT = True
```

### 3. **Validation and Defaults**
```python
# Validated configuration with fallbacks
def get_log_level():
    level = os.getenv('LOG_LEVEL', 'INFO').upper()
    return level if level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'] else 'INFO'
```

## 🚀 Usage Examples

### **Basic Configuration Import**
```python
from src.config import PAGE_CONFIG, setup_logging
from src.config.paths import ASSETS, DB_ROOT
from src.config.settings import PRIMARY_COLOR, DEFAULT_USERS

# Use in application
st.set_page_config(**PAGE_CONFIG)
logger = setup_logging()
```

### **Path Operations**
```python
from src.config.paths import USERS_FILE, ensure_dir

# Ensure directory exists before file operations
ensure_dir(USERS_FILE.parent)

# Safe file operations
if USERS_FILE.exists():
    data = USERS_FILE.read_text()
```

### **Settings Access**
```python
from src.config.settings import TREE_CO2_ABSORPTION, PRIMARY_COLOR

# Use in calculations
trees_equivalent = co2_total / TREE_CO2_ABSORPTION

# Use in UI theming
st.markdown(f"<style>color: {PRIMARY_COLOR};</style>")
```

## 🔒 Security Considerations

### **Sensitive Configuration**
- Default passwords should be changed in production
- Consider environment variables for secrets
- Log levels should be appropriate for deployment environment

### **Path Security**
- All paths are validated before use
- Directory creation handles permissions appropriately
- File conflicts are resolved safely with backups

### **Configuration Validation**
- Settings are validated at import time
- Invalid configurations fall back to safe defaults
- Environment overrides are sanitized

## 🛠️ Development Guidelines

### **Adding New Configuration**

1. **Determine Category**: Settings, paths, or logging configuration
2. **Add Constants**: Define in appropriate module (settings.py, paths.py)
3. **Update Exports**: Add to `__init__.py` if needed for external access
4. **Document Usage**: Add examples and interaction notes
5. **Test Validation**: Ensure proper defaults and error handling

### **Environment Customization**

1. **Use Environment Variables**: For deployment-specific settings
2. **Provide Defaults**: Always have sensible fallback values
3. **Validate Input**: Check environment variable values
4. **Document Variables**: List all supported environment variables

### **Path Management**

1. **Use Path Constants**: Never hardcode file paths in other modules
2. **Cross-Platform**: Use `pathlib.Path` for platform independence
3. **Error Handling**: Handle missing directories and permissions
4. **Backup Strategy**: Implement conflict resolution for important files

## 🔗 Integration Points

### **Upstream Dependencies**
- Python standard library (`pathlib`, `logging`, `os`)
- Cross-platform file system operations

### **Downstream Consumers**
- [`../../main.py`](../../main.py): Application configuration and logging setup
- [`../auth/README.md`](../auth/README.md): User file paths and authentication settings
- [`../database/README.md`](../database/README.md): Database file paths and Excel settings
- [`../ui/README.md`](../ui/README.md): Theme colors and UI configuration
- [`../reports/README.md`](../reports/README.md): Template paths and export settings
- All modules: Logging configuration and path access

## 📊 Performance Considerations

### **Import Time**
- Configuration is loaded once at import time
- Path validation occurs during module initialization
- Minimal runtime overhead for configuration access

### **File System Operations**
- Directory creation is performed once at startup
- Path resolution uses cached Path objects
- File existence checks are minimized

## 🎯 Future Enhancements

1. **Dynamic Configuration**: Runtime configuration updates
2. **Configuration Validation**: Schema-based validation
3. **Environment Profiles**: Development/staging/production profiles
4. **Configuration UI**: Admin interface for settings management
5. **Encrypted Configuration**: Secure storage for sensitive settings
6. **Configuration Versioning**: Track configuration changes over time