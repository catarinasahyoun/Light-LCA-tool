# UI Module

## 📋 Overview

The UI module (`src/ui/`) provides reusable user interface components and styling for the TCHAI LCA Tool. It centralizes UI logic and ensures consistent design across all pages.

## 🏗️ Architecture

```
ui/
├── __init__.py          # UI component exports
├── styling.py           # CSS themes and visual design
├── sidebar.py           # Navigation sidebar component
├── header.py            # Application header component
└── auth_components.py   # Authentication UI elements
```

## 🔧 Components

### 1. **Components** ([`components.py`](components.py))
**Purpose**: Reusable Streamlit UI components

**Key Components**:
- **Form Components**: Validated input fields, dropdowns, sliders
- **Display Components**: Cards, panels, info boxes
- **Data Components**: Tables, charts, progress indicators
- **Layout Components**: Containers, columns, expanders

**Features**:
- **Consistent styling**: Unified look and feel across pages
- **Validation integration**: Built-in data validation and error handling
- **Responsive design**: Adaptive layouts for different screen sizes
- **Theme support**: Light/dark mode compatibility

**Integration Points**:
- **Config**: Styling constants via [`../config/README.md`](../config/README.md)
- **Models**: Data validation via [`../models/README.md`](../models/README.md)
- **Used by**: All page modules via [`../pages/README.md`](../pages/README.md)

### 2. **Sidebar** (`sidebar.py`)
**Purpose**: Main navigation component

**Key Features**:
- Page navigation menu
- User context display
- Language selection
- Responsive collapse/expand

### 3. **Header** (`header.py`)
**Purpose**: Application header and branding

**Key Features**:
- Logo and branding display
- Application title
- User information
- Breadcrumb navigation

### 4. **Auth Components** (`auth_components.py`)
**Purpose**: Authentication-related UI elements

**Key Features**:
- Login/logout forms
- User registration interface
- Password reset functionality
- Session management UI

## 🎨 Design System

### **Color Palette**
- Primary: `#6366f1` (Indigo)
- Background: `#f8fafc` (Light gray)
- Success: `#10b981` (Green)
- Error: `#ef4444` (Red)
- Text: `#1f2937` (Dark gray)

### **Typography**
- Font Family: PP Neue Montreal (custom), sans-serif
- Heading weights: 500-700
- Body text: 400
- Code/monospace: Courier New

### **Component Standards**
- Consistent spacing (8px grid)
- Standardized button styles
- Form validation styling
- Loading state indicators

## 🔄 Component Patterns

### **Reusable Components**
```python
class ComponentName:
    @staticmethod
    def render():
        # Component logic
        # Streamlit UI elements
        # Return any needed values
```

### **State Management**
```python
# Components access session state
user = st.session_state.get('auth_user')

# Components can modify state
st.session_state.page = selected_page
```

## 🚀 Usage Examples

### **Apply Styling**
```python
from src.ui import UIStyles

# Apply global theme
UIStyles.apply_theme()
```

### **Render Navigation**
```python
from src.ui import Sidebar

# Render sidebar and get selected page
sidebar = Sidebar()
page = sidebar.render()
```

### **Authentication Check**
```python
from src.ui import AuthComponents

# Check if user is authenticated
if not AuthComponents.check_authentication():
    st.stop()
```

## 🔗 Integration Points

### **Used By**
- [`../../main.py`](../../main.py): Application styling and navigation
- [`../pages/README.md`](../pages/README.md): Authentication checks and UI consistency
- All application components for consistent styling

### **Dependencies**
- `streamlit`: UI framework
- [`../auth/README.md`](../auth/README.md): Authentication logic
- [`../config/README.md`](../config/README.md): Theme configuration and settings
- [`../utils/README.md`](../utils/README.md): Internationalization