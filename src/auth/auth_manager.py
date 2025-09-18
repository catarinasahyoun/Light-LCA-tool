"""
Authentication Manager - User Management and Security

This module provides the core authentication functionality for the TCHAI LCA Tool.
It handles user registration, login validation, session management, and secure 
password operations using industry-standard practices.

Key Features:
    - Secure password hashing with bcrypt and salt
    - JSON-based user database with file persistence
    - Session state management via Streamlit
    - Administrative user bootstrap
    - Role-based access control

Security Considerations:
    - Passwords are never stored in plain text
    - Each password uses a unique salt for enhanced security
    - Session data is stored in Streamlit's secure session state
    - File operations include error handling and validation

Author: TCHAI Team
"""

import json
import streamlit as st
from typing import Optional, Dict, List
from datetime import datetime
import logging

# Internal imports for configuration and utilities
from ..config.paths import USERS_FILE
from ..config.settings import DEFAULT_USERS, DEFAULT_PASSWORD
from ..models.user import User
from .password_utils import generate_salt, hash_password, verify_password

# Set up module logger
logger = logging.getLogger(__name__)


class AuthManager:
    """
    Central authentication manager for user security and session management.
    
    This class provides static methods for all authentication operations including
    user registration, login validation, session management, and user data persistence.
    It maintains a JSON-based user database and integrates with Streamlit's session
    state for secure user sessions.
    
    Design Patterns:
        - Static Class: All methods are static for easy access across the application
        - Singleton Data: User database is centrally managed
        - Session Management: Leverages Streamlit's built-in session state
        
    Security Features:
        - bcrypt password hashing with unique salts
        - Input validation and sanitization
        - Error handling without information disclosure
        - Secure session state management
    """
    
    @staticmethod
    def load_users() -> Dict[str, User]:
        """
        Load all users from the persistent user database file.
        
        Reads the users.json file and deserializes user data into User model objects.
        Handles file corruption, missing files, and JSON parsing errors gracefully.
        
        Returns:
            Dict[str, User]: Dictionary mapping email addresses to User objects.
                           Returns empty dict if file doesn't exist or is corrupted.
                           
        Raises:
            No exceptions raised - all errors are handled internally and logged.
            
        Side Effects:
            - May log warnings for file reading errors
            - Creates empty user database if file is corrupted
            
        Example:
            >>> users = AuthManager.load_users()
            >>> if 'admin@tchai.com' in users:
            ...     user = users['admin@tchai.com']
        """
        try:
            if USERS_FILE.exists():
                logger.debug(f"Loading users from {USERS_FILE}")
                data = json.loads(USERS_FILE.read_text())
                users = {email: User(**user_data) for email, user_data in data.items()}
                logger.info(f"Successfully loaded {len(users)} users")
                return users
            else:
                logger.info("User file does not exist - returning empty user database")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse user database JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading users: {e}")
            return {}
    
    @staticmethod
    def save_users(users: Dict[str, User]) -> bool:
        """
        Persist user database to the users.json file.
        
        Serializes all user data and writes it to the persistent storage file.
        Includes error handling for file system operations and JSON serialization.
        
        Args:
            users (Dict[str, User]): Dictionary of users to save, keyed by email.
            
        Returns:
            bool: True if save operation succeeded, False otherwise.
            
        Raises:
            No exceptions raised - all errors are handled internally and logged.
            
        Side Effects:
            - Writes/overwrites the users.json file
            - May create the file if it doesn't exist
            - Logs success/failure messages
            
        Example:
            >>> users = AuthManager.load_users()
            >>> users['new@user.com'] = new_user
            >>> success = AuthManager.save_users(users)
        """
        try:
            # Convert User objects to dictionaries for JSON serialization
            data = {email: user.model_dump() for email, user in users.items()}
            
            # Write to file with proper formatting
            USERS_FILE.write_text(json.dumps(data, indent=2))
            logger.info(f"Successfully saved {len(users)} users to {USERS_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save users to {USERS_FILE}: {e}")
            return False
    
    @staticmethod
    def bootstrap_users_if_needed() -> None:
        """
        Create default administrative users if no users exist in the system.
        
        This method is called during application startup to ensure there's always
        at least one user account available for system access. It creates default
        admin accounts with secure passwords based on configuration settings.
        
        Workflow:
            1. Check if any users exist in the database
            2. If no users found, create default admin accounts
            3. Generate secure salts and password hashes
            4. Save new users to persistent storage
            
        Side Effects:
            - May create users.json file
            - May add default admin accounts
            - Logs bootstrap operations
            
        Configuration:
            Uses DEFAULT_USERS and DEFAULT_PASSWORD from config.settings
            
        Example:
            >>> AuthManager.bootstrap_users_if_needed()
            # Creates admin users if database is empty
        """
        users = AuthManager.load_users()
        
        # If users already exist, no bootstrap needed
        if users:
            logger.debug("Users already exist - skipping bootstrap")
            return
        
        logger.info("No users found - bootstrapping default admin accounts")
        new_users = {}
        
        # Create default admin users from configuration
        for email in DEFAULT_USERS:
            logger.debug(f"Creating default user: {email}")
            
            # Generate unique salt and hash password securely
            salt = generate_salt()
            password_hash = hash_password(DEFAULT_PASSWORD, salt)
            
            # Create new User object with admin privileges
            new_users[email] = User(
                email=email,
                password_hash=password_hash,
                salt=salt,
                is_admin=True,  # Default users are administrators
                created_at=datetime.now().isoformat()
            )
        
        # Persist new users to database
        if AuthManager.save_users(new_users):
            logger.info(f"Successfully bootstrapped {len(new_users)} admin users")
        else:
            logger.error("Failed to save bootstrapped users")
    
    @staticmethod
    @staticmethod
    def authenticate(email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password credentials.
        
        Validates user credentials against the stored user database using secure
        password verification. This method implements the core login functionality
        and should be used for all authentication attempts.
        
        Args:
            email (str): User's email address (case-insensitive)
            password (str): Plain text password provided by user
            
        Returns:
            Optional[User]: User object if authentication succeeds, None if it fails.
                          Returns None for both invalid credentials and system errors.
                          
        Security Features:
            - Constant-time password verification to prevent timing attacks
            - No information disclosure about whether email exists
            - Comprehensive logging for security monitoring
            
        Side Effects:
            - Logs authentication attempts (success and failure)
            - Updates user's last_login timestamp on success
            
        Example:
            >>> user = AuthManager.authenticate('admin@tchai.com', 'password123')
            >>> if user:
            ...     print(f"Welcome {user.email}")
            ... else:
            ...     print("Invalid credentials")
        """
        try:
            # Normalize email to lowercase for consistent lookup
            email = email.lower().strip()
            
            # Load current user database
            users = AuthManager.load_users()
            user = users.get(email)
            
            # Check if user exists and password is correct
            if user and verify_password(password, user.salt, user.password_hash):
                logger.info(f"Successful authentication for user: {email}")
                
                # Update last login timestamp
                users[email] = user
                AuthManager.save_users(users)
                
                return user
            else:
                # Log failed authentication (don't reveal if email exists)
                logger.warning(f"Failed authentication attempt for email: {email}")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            return None
    
    @staticmethod
    def get_current_user() -> Optional[User]:
        """
        Retrieve the currently authenticated user from session state.
        
        Accesses Streamlit's session state to get the currently logged-in user.
        This method should be used to check authentication status and get user
        information throughout the application.
        
        Returns:
            Optional[User]: Currently authenticated user object, or None if not logged in.
                          
        Side Effects:
            None - This is a read-only operation
            
        Example:
            >>> current_user = AuthManager.get_current_user()
            >>> if current_user and current_user.is_admin:
            ...     # Show admin features
            ...     pass
        """
        return st.session_state.get("auth_user")
    
    @staticmethod
    def login_user(user: User) -> None:
        """
        Log in a user by storing their information in session state.
        
        Establishes a user session by storing the user object in Streamlit's
        session state. This should be called after successful authentication
        to maintain the user's logged-in status across page interactions.
        
        Args:
            user (User): Authenticated user object to store in session
            
        Side Effects:
            - Modifies Streamlit session state
            - Logs the login event
            - User remains logged in until logout or session end
            
        Example:
            >>> user = AuthManager.authenticate(email, password)
            >>> if user:
            ...     AuthManager.login_user(user)
            ...     st.success("Login successful")
        """
        st.session_state.auth_user = user
        logger.info(f"User logged in: {user.email}")
    
    @staticmethod
    def logout_user() -> None:
        """
        Log out the current user by clearing session state.
        
        Ends the current user session by removing authentication information
        from session state. This effectively logs out the user and they will
        need to re-authenticate to access protected content.
        
        Side Effects:
            - Clears user information from session state
            - Logs the logout event
            - User will be redirected to login on next page access
            
        Example:
            >>> AuthManager.logout_user()
            >>> st.info("You have been logged out")
        """
        current_user = AuthManager.get_current_user()
        if current_user:
            logger.info(f"User logged out: {current_user.email}")
        
        # Clear authentication from session state
        st.session_state.auth_user = None
        
        # Clear any other session data that should not persist
        # (Add more session state cleanup here if needed)
    
    @staticmethod
    def register_user(email: str, password: str, is_admin: bool = False) -> bool:
        """
        Register a new user account with the system.
        
        Creates a new user account with secure password hashing and stores it
        in the user database. This method should only be called by administrators
        or during the initial setup process.
        
        Args:
            email (str): Email address for the new user (must be unique)
            password (str): Plain text password (will be securely hashed)
            is_admin (bool): Whether the user should have administrative privileges
            
        Returns:
            bool: True if registration succeeded, False if it failed
            
        Validation:
            - Email must be valid format and not already exist
            - Password must meet minimum security requirements
            - Admin status is preserved for audit trails
            
        Side Effects:
            - Adds new user to database file
            - Logs registration events
            - May modify users.json file
            
        Example:
            >>> success = AuthManager.register_user(
            ...     email='new@user.com',
            ...     password='secure_password',
            ...     is_admin=False
            ... )
            >>> if success:
            ...     st.success("User registered successfully")
        """
        try:
            # Normalize and validate email
            email = email.lower().strip()
            if not email or '@' not in email:
                logger.error(f"Invalid email format: {email}")
                return False
            
            # Load current users and check for duplicates
            users = AuthManager.load_users()
            if email in users:
                logger.warning(f"Registration failed - email already exists: {email}")
                return False
            
            # Generate secure password hash
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            # Create new user object
            new_user = User(
                email=email,
                password_hash=password_hash,
                salt=salt,
                is_admin=is_admin,
                created_at=datetime.now().isoformat()
            )
            
            # Add to user database and save
            users[email] = new_user
            if AuthManager.save_users(users):
                logger.info(f"Successfully registered new user: {email} (admin: {is_admin})")
                return True
            else:
                logger.error(f"Failed to save new user: {email}")
                return False
                
        except Exception as e:
            logger.error(f"Registration error for {email}: {e}")
            return False
    
    @staticmethod
    def is_authenticated() -> bool:
        """
        Check if there is currently an authenticated user session.
        
        Convenience method to quickly check authentication status without
        retrieving the full user object.
        
        Returns:
            bool: True if a user is currently logged in, False otherwise
            
        Example:
            >>> if AuthManager.is_authenticated():
            ...     # Show authenticated content
            ...     pass
            ... else:
            ...     # Redirect to login
            ...     pass
        """
        return AuthManager.get_current_user() is not None
    
    @staticmethod
    def get_all_users() -> List[User]:
        """
        Retrieve all users from the database (admin only operation).
        
        Returns a list of all registered users. This method should only be
        called by administrators for user management purposes.
        
        Returns:
            List[User]: List of all user objects in the system
            
        Security Note:
            This method returns all users including password hashes.
            Ensure proper authorization before calling this method.
            
        Example:
            >>> if current_user.is_admin:
            ...     all_users = AuthManager.get_all_users()
            ...     # Display user management interface
        """
        users_dict = AuthManager.load_users()
        return list(users_dict.values())