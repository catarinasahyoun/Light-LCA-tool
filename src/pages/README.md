# Pages Module

## 📋 Overview

### 2. **Tool Page** ([`tool_page.py`](tool_page.py))
**Purpose**: Main LCA assessment interface

**Key Features**:
- Material selection and configuration
- Quantity input and validation
- Real-time calculation display
- Results visualization

**Components**:
- Material browser and search
- Input forms with validation
- Calculation engine integration
- Results display components

**Integration Points**:
- **Database**: Material data access via [`../database/README.md`](../database/README.md)
- **Utils**: LCA calculations via [`../utils/README.md`](../utils/README.md)
- **Models**: Data validation via [`../models/README.md`](../models/README.md)
- **UI**: Display components via [`../ui/README.md`](../ui/README.md)le ### 1. **Login Page** ([`login_page.py`](login_page.py))
**Purpose**: User authentication interface

**Key Features**:
- Username/password authentication form
- Registration for new users
- Password validation and security
- Session management integration

**Integration Points**:
- **Auth**: Uses authentication services from [`../auth/README.md`](../auth/README.md)
- **UI**: Uses form components from [`../ui/README.md`](../ui/README.md)
- **Config**: Uses styling from [`../config/README.md`](../config/README.md)es/`) contains all Streamlit page components that make up the user interface of the TCHAI LCA Tool. Each page handles specific functionality and user interactions within the application.

## 🏗️ Architecture

```
pages/
├── __init__.py          # Page exports and routing
├── tool_page.py         # Main LCA input and data entry
├── results_page.py      # Results analysis and visualization
├── user_guide_page.py   # Documentation and help
├── settings_page.py     # Administrative configuration
└── versions_page.py     # Version management and saved assessments
```

## 🔧 Page Components

### 1. **Tool Page** (`tool_page.py`)
**Purpose**: Main LCA data input interface

**Key Features**:
- Material selection from database
- Mass input and validation
- Processing steps configuration
- Real-time calculation preview
- Data validation and error handling

**Interactions**:
- **Uses**: `database/` for material data
- **Uses**: `models/assessment.py` for data validation
- **Updates**: Session state with assessment data

### 4. **Reports Page** ([`reports_page.py`](reports_page.py))
**Purpose**: LCA report generation and export

**Key Features**:
- Report template selection
- Customizable report parameters
- Multiple export formats (PDF, DOCX)
- Report preview and validation

**Report Types**:
- Summary assessments
- Detailed material analysis
- Comparative studies
- Custom formatted reports

**Integration Points**:
- **Reports**: Report generation via [`../reports/README.md`](../reports/README.md)
- **Utils**: Data processing via [`../utils/README.md`](../utils/README.md)
- **Models**: Data validation via [`../models/README.md`](../models/README.md)
- **Config**: Template paths via [`../config/README.md`](../config/README.md)

### 3. **User Guide Page** (`user_guide_page.py`)
**Purpose**: Application documentation and help

**Key Features**:
- Step-by-step usage instructions
- Feature explanations and examples
- Troubleshooting guides
- Video tutorials and resources

### 3. **Settings Page** ([`settings_page.py`](settings_page.py))
**Purpose**: Application configuration and database management

**Key Features**:
- Database selection and switching
- Version management interface
- User preferences configuration
- System settings access

**Administrative Functions**:
- Database upload and validation
- User account management
- Application theme customization
- Export/import settings

**Integration Points**:
- **Database**: Database management via [`../database/README.md`](../database/README.md)
- **Auth**: User management via [`../auth/README.md`](../auth/README.md)
- **Config**: Settings access via [`../config/README.md`](../config/README.md)
- **Utils**: Version control via [`../utils/README.md`](../utils/README.md)

### 5. **Versions Page** (`versions_page.py`)
**Purpose**: Version management for saved assessments

**Key Features**:
- Save/load assessment versions
- Version comparison and analysis
- Assessment history and metadata
- Export/import functionality

**Interactions**:
- **Uses**: `utils/version_manager.py` for version operations
- **Uses**: `models/assessment.py` for data validation

## 🔄 Page Flow

```
Sidebar Navigation
├── Authentication Check
├── Page Route Selection
├── Page Render
├── User Interaction
├── Data Processing
└── State Update
```

## 🚀 Common Patterns

### **Page Structure**
```python
class PageName:
    @staticmethod
    def render():
        st.header("Page Title")
        # Page content
        # User interactions
        # Data processing
```

### **Authentication Check**
```python
# All pages expect user to be authenticated
if not AuthComponents.check_authentication():
    st.stop()
```

### **State Management**
```python
# Access session state
assessment = st.session_state.get('assessment', {})

# Update session state
st.session_state.assessment = new_data
```

## 🔗 Integration Points

### **Dependencies**
- `streamlit`: UI framework
- [`../auth/README.md`](../auth/README.md): Authentication checking
- [`../ui/README.md`](../ui/README.md): Reusable UI components
- [`../models/README.md`](../models/README.md): Data validation
- [`../database/README.md`](../database/README.md): Data access
- [`../utils/README.md`](../utils/README.md): Business logic
- [`../reports/README.md`](../reports/README.md): Document generation

### **State Management**
- All pages use Streamlit session state
- Common data structures across pages
- Persistent user preferences