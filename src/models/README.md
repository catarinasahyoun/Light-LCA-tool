# Models Module

## 📋 Overview

The models module (`src/models/`) defines the core data structures and validation schemas for the TCHAI LCA Tool using Pydantic. It provides type-safe, validated data models that ensure data integrity throughout the application.

## 🏗️ Architecture

```
models/
├── __init__.py          # Model exports and type definitions
├── assessment.py        # LCA assessment data models
└── user.py             # User account and authentication models
```

## 🔧 Components

### 1. **Assessment Models** (`assessment.py`)
**Purpose**: Define LCA assessment data structures and validation

**Key Models**:
- `Assessment`: Complete LCA assessment with materials, processes, and metadata
- `Material`: Individual material properties and carbon footprint data
- `Process`: Manufacturing/processing step with carbon impact
- `LifeCycleData`: Aggregated lifecycle assessment results

### 2. **User Models** (`user.py`) 
**Purpose**: User account management and authentication data

**Key Models**:
- `User`: User account with authentication and profile information
- `UserProfile`: Extended user profile data and preferences
- `UserSession`: Session management and authentication state

## 🔄 Model Interactions

```
Pages/UI → Models → Database/Utils
    ↓        ↓         ↓
Input → Validation → Storage/Calculation
```

## 🚀 Usage Examples

### **Assessment Models**
```python
from src.models import Assessment, Material

# Create material
material = Material(
    name="Steel",
    co2e_per_kg=2.5,
    recycled_content=30.0,
    circularity="medium"
)

# Create assessment
assessment = Assessment(
    name="Building Assessment",
    materials=[material],
    lifetime_weeks=520
)
```

### **User Models**
```python
from src.models import User

# Create user
user = User(
    email="user@example.com",
    password_hash="hashed_password",
    is_admin=False
)
```

## 🛡️ Validation Features

- **Type Safety**: Automatic type checking and conversion
- **Field Validation**: Custom validators for business rules
- **Required Fields**: Mandatory field enforcement
- **Default Values**: Sensible defaults for optional fields
- **Data Serialization**: JSON conversion for storage/API

## 🔗 Integration Points

### **Used By**
- [`../database/README.md`](../database/README.md): Data parsing and storage
- [`../pages/README.md`](../pages/README.md): Form validation and display
- [`../utils/README.md`](../utils/README.md): Calculations and business logic
- [`../auth/README.md`](../auth/README.md): User management
- [`../reports/README.md`](../reports/README.md): Data serialization for reports

### **Dependencies**
- `pydantic`: Data validation and serialization
- `typing`: Type hints and annotations
- `datetime`: Timestamp handling