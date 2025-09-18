# Authentication Module

## 📋 Overview

The authentication module (`src/auth/`) provides secure user management and session handling for the TCHAI LCA Tool. It implements password-based authentication with role-based access control and session persistence.

## 🏗️ Architecture

```
auth/
├── __init__.py          # Module exports and initialization
├── auth_manager.py      # Core authentication logic and user management
└── password_utils.py    # Password hashing and verification utilities
```

## 🔧 Components

### 1. **AuthManager** (`auth_manager.py`)
**Purpose**: Central authentication controller and user management

**Key Responsibilities**:
- User registration and login validation
- Session state management  
- User database operations (JSON-based storage)
- Administrative user bootstrap
- Password policy enforcement

**Interactions**:
- **Uses**: [`password_utils.py`](password_utils.py) for secure password operations
- **Uses**: [`config/paths.py`](../config/paths.py) for user data file locations
- **Used by**: [`main.py`](../../main.py) for application bootstrap
- **Used by**: [`ui/auth_components.py`](../ui/auth_components.py) for login/logout UI

**Key Methods**:
```python
@classmethod
def bootstrap_users_if_needed() -> None
    # Creates default admin user if no users exist

@classmethod  
def authenticate_user(username: str, password: str) -> bool
    # Validates user credentials against stored data

@classmethod
def register_user(username: str, password: str, is_admin: bool = False) -> bool
    # Creates new user account with validation

@classmethod
def get_current_user() -> Optional[User]
    # Retrieves current authenticated user from session
```

### 2. **Password Utilities** (`password_utils.py`)
**Purpose**: Secure password handling and cryptographic operations

**Key Responsibilities**:
- Password hashing using bcrypt algorithm
- Password verification and comparison
- Salt generation for enhanced security
- Secure random password generation

**Interactions**:
- **Used by**: [`auth_manager.py`](auth_manager.py) for all password operations
- **Dependencies**: `bcrypt` library for cryptographic functions

**Key Functions**:
```python
def hash_password(password: str) -> str
    # Generates secure bcrypt hash of password

def verify_password(password: str, hashed: str) -> bool  
    # Verifies password against stored hash

def generate_random_password(length: int = 12) -> str
    # Creates cryptographically secure random password
```

## 🔄 Authentication Flow

### 1. **Application Bootstrap**
```
main.py startup
├── AuthManager.bootstrap_users_if_needed()
├── Check if users.json exists
├── Create default admin if no users found
└── Initialize authentication system
```

### 2. **User Login Process**
```
User enters credentials
├── AuthComponents.render_login_form()
├── AuthManager.authenticate_user(username, password)
├── password_utils.verify_password(password, stored_hash)
├── Update session state with user info
└── Redirect to main application
```

### 3. **Session Management**
```
Each page request
├── AuthComponents.check_authentication()
├── Verify session state contains valid user
├── Check session timeout (if implemented)
└── Allow/deny access to protected content
```

### 4. **User Registration**
```
Admin adds new user
├── SettingsPage renders user management
├── AuthManager.register_user(details)
├── password_utils.hash_password(new_password)
├── Store user in users.json
└── Update user database
```

## 💾 Data Storage

### **User Data Format** (`assets/users.json`)
```json
{
  "users": [
    {
      "username": "admin",
      "password_hash": "$2b$12$...",
      "is_admin": true,
      "created_at": "2025-09-17T10:30:00Z",
    }
  ]
}
```

### **Session State Structure**
```python
st.session_state.user = {
    "username": "admin",
    "is_admin": True,
    "authenticated": True,
}
```

## 🔒 Security Features

### 1. **Password Security**
- **bcrypt hashing**: Industry-standard password hashing
- **Salt generation**: Unique salt for each password
- **Configurable rounds**: Adjustable complexity (default: 12)
- **Minimum length**: Enforced password requirements

### 2. **Session Security**
- **Session state**: Temporary session storage in Streamlit
- **Authentication checks**: Required for all protected pages
- **Automatic logout**: On browser close/session end

### 3. **Administrative Controls**
- **Admin bootstrap**: Automatic admin creation on first run
- **Role-based access**: Admin vs regular user permissions
- **User management**: Admin can create/modify users

## 🚀 Usage Examples

### **Basic Authentication Check**
```python
from src.auth import AuthManager
from src.ui import AuthComponents

# Check if user is authenticated
if not AuthComponents.check_authentication():
    st.stop()  # Redirect to login

# Get current user info
user = AuthManager.get_current_user()
if user and user.is_admin:
    # Show admin features
    pass
```

### **User Registration**
```python
from src.auth import AuthManager

# Register new user (admin only)
success = AuthManager.register_user(
    username="newuser",
    password="secure_password",
    is_admin=False
)

if success:
    st.success("User created successfully")
else:
    st.error("Registration failed")
```

### **Password Validation**
```python
from src.auth.password_utils import verify_password, hash_password

# Hash password for storage
hashed = hash_password("user_password")

# Verify password during login
is_valid = verify_password("user_password", hashed)
```

## 🔧 Configuration

### **Environment Variables**
- `BCRYPT_ROUNDS`: Password hashing complexity (default: 12)
- `SESSION_TIMEOUT`: Session timeout in minutes (future feature)

### **File Paths**
- User database: `assets/users.json`
- Logs: `assets/logs/app.log`

## 🛠️ Development Guidelines

### **Adding New Authentication Features**

1. **Extend AuthManager**: Add new methods to `auth_manager.py`
2. **Update Models**: Modify user data structure if needed
3. **Add UI Components**: Create forms in `ui/auth_components.py`
4. **Test Security**: Ensure proper validation and sanitization

### **Security Best Practices**

1. **Never store plain passwords**: Always use password hashing
2. **Validate input**: Sanitize all user inputs
3. **Check permissions**: Verify user roles before sensitive operations
4. **Log security events**: Monitor authentication attempts
5. **Update dependencies**: Keep bcrypt and other security libraries current

## 🔗 Integration Points

### **Upstream Dependencies**
- `config/paths.py`: File path configuration
- `models/user.py`: User data model definition

### **Downstream Consumers**
- `main.py`: Application bootstrap and routing
- `ui/auth_components.py`: Login/logout UI components
- `pages/settings_page.py`: User management interface
- All protected pages: Authentication requirement

## 📊 Performance Considerations

### **Password Hashing**
- bcrypt is intentionally slow (security feature)
- Consider caching authenticated sessions
- Balance security vs performance with bcrypt rounds

### **User Database**
- JSON file storage suitable for small user bases
- Consider database migration for large deployments
- File locking may be needed for concurrent access

## 🎯 Future Enhancements

1. **Session Timeout**: Automatic logout after inactivity
2. **Password Reset**: Email-based password recovery
3. **Multi-factor Authentication**: TOTP/SMS verification
4. **OAuth Integration**: Google/Microsoft login
5. **Audit Logging**: Detailed security event logging
6. **Database Backend**: Migration from JSON to SQL database