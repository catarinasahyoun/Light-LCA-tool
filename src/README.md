# TCHAI LCA Tool - Source Code Documentation

## 🏗️ Architecture Overview

The TCHAI Life Cycle Assessment (LCA) Tool is built with a modular architecture that separates concerns into distinct, well-defined modules. This design promotes maintainability, testability, and scalability.

## 📁 Module Structure

```
src/
├── auth/           # Authentication and user management
├── config/         # Configuration, paths, and settings
├── database/       # Data management and Excel parsing
├── models/         # Data models and validation
├── pages/          # Streamlit page components
├── reports/        # PDF/DOCX report generation
├── ui/             # User interface components
└── utils/          # Utility functions and calculations
```

## 🔄 Module Interactions

### Core Flow
```
main.py → config → auth → ui → pages → models/database/utils → reports
```

### Detailed Interactions

#### 1. **Application Bootstrap** (`main.py`)
- Initializes Streamlit configuration from `config/`
- Sets up logging via `config/logging_config.py`
- Applies UI styling from `ui/styling.py`
- Bootstraps authentication system from `auth/`

#### 2. **Authentication Layer** (`auth/`)
- Manages user sessions and security
- Interacts with: `ui/auth_components.py`, `config/paths.py`
- Used by: `main.py`, all protected pages

#### 3. **User Interface Layer** (`ui/`)
- Provides reusable UI components
- Interacts with: `config/settings.py`, `auth/`, `utils/i18n.py`
- Used by: `main.py`, `pages/`

#### 4. **Page Layer** (`pages/`)
- Implements individual application screens
- Interacts with: `models/`, `database/`, `utils/`, `reports/`
- Coordinates business logic and user interactions

#### 5. **Data Layer** (`models/` + `database/`)
- **Models**: Define data structures and validation
- **Database**: Handle Excel file parsing and data persistence
- Interacts with: `config/paths.py`, `utils/calculations.py`

#### 6. **Business Logic** (`utils/`)
- LCA calculations and algorithms
- File operations and utilities
- Version management
- Interacts with: All modules as needed

#### 7. **Report Generation** (`reports/`)
- PDF and DOCX report creation
- Template processing
- Interacts with: `utils/`, `config/paths.py`

## 🚀 Application Flow

### 1. **Startup Sequence**
```python
main.py
├── Configure Streamlit (config/)
├── Setup logging (config/)
├── Apply UI theme (ui/)
├── Bootstrap users (auth/)
├── Initialize translator (utils/)
└── Render application
```

### 2. **Request Lifecycle**
```python
User Request
├── Sidebar navigation (ui/)
├── Authentication check (auth/)
├── Route to page (pages/)
├── Process data (models/database/)
├── Perform calculations (utils/)
├── Generate reports (reports/)
└── Return response
```

### 3. **Data Flow**
```python
Excel Files (database/)
├── Parse and validate (database/parsers.py)
├── Store in models (models/assessment.py)
├── Calculate LCA metrics (utils/calculations.py)
├── Display results (pages/results_page.py)
└── Generate reports (reports/)
```

## 🔧 Key Design Patterns

### 1. **Modular Design**
- Each module has a single, well-defined responsibility
- Clear interfaces between modules
- Minimal coupling, high cohesion

### 2. **Configuration Management**
- Centralized configuration in `config/`
- Environment-specific settings
- Path management for cross-platform compatibility

### 3. **Data Validation**
- Pydantic models for type safety
- Input validation at data entry points
- Error handling and user feedback

### 4. **UI Component Architecture**
- Reusable UI components in `ui/`
- Consistent styling and theming
- Separation of presentation and logic

### 5. **Report Generation Pipeline**
- Template-based report generation
- Multiple output formats (PDF, DOCX, TXT)
- Graceful fallbacks for missing dependencies

## 📊 Dependencies Between Modules

| Module | Depends On | Used By |
|--------|------------|---------|
| `config/` | None | All modules |
| `auth/` | `config/`, `ui/` | `main.py`, `pages/` |
| `models/` | `config/` | `database/`, `pages/`, `utils/` |
| `database/` | `config/`, `models/` | `pages/`, `utils/` |
| `ui/` | `config/`, `auth/`, `utils/` | `main.py`, `pages/` |
| `utils/` | `config/`, `models/` | `pages/`, `reports/` |
| `pages/` | All modules | `main.py` |
| `reports/` | `config/`, `utils/` | `pages/` |

## 🛠️ Development Guidelines

### 1. **Adding New Features**
1. Identify the appropriate module for the feature
2. Define data models if needed (`models/`)
3. Implement business logic (`utils/`)
4. Create UI components (`pages/`, `ui/`)
5. Add configuration if needed (`config/`)

### 2. **Module Communication**
- Use clear, documented interfaces
- Avoid circular dependencies
- Pass data through function parameters
- Use Streamlit session state for temporary data

### 3. **Error Handling**
- Log errors using the configured logger
- Provide user-friendly error messages
- Implement graceful degradation where possible

### 4. **Testing Strategy**
- Unit tests for utility functions
- Integration tests for data flow
- UI tests for user interactions

## 📝 Documentation Standards

Each module contains:
- `README.md` - Module overview and usage
- Detailed docstrings in Python files
- Type hints for all functions
- Inline comments for complex logic

## 🔍 Quick Start for Developers

1. **Understand the Architecture**: Read this README and module READMEs
2. **Set Up Environment**: Install dependencies and configure Python environment
3. **Explore Key Files**:
   - `main.py` - Application entry point
   - `config/settings.py` - Configuration constants
   - `pages/tool_page.py` - Main LCA input interface
   - `utils/calculations.py` - Core LCA algorithms
4. **Run the Application**: `streamlit run main.py`
5. **Make Changes**: Follow the modular structure and update documentation

## 🎯 Next Steps

For detailed information about each module, see the README.md files in each subdirectory:
- [Authentication Module](auth/README.md) - User management and security
- [Configuration Module](config/README.md) - Settings and path management
- [Database Module](database/README.md) - Excel parsing and data management
- [Models Module](models/README.md) - Data structures and validation
- [Pages Module](pages/README.md) - Streamlit page components
- [Reports Module](reports/README.md) - PDF/DOCX generation
- [UI Module](ui/README.md) - User interface components
- [Utils Module](utils/README.md) - Utilities and calculations

## 📖 Related Documentation

- [Main Application Entry Point](../main.py) - Application bootstrap and routing
- [Project Root Documentation](../README.md) - Project overview and setup
- [Requirements](../requirements.txt) - Python dependencies