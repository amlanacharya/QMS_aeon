# settings_service.py
"""
Settings service for managing application configuration.
This module follows the Single Responsibility Principle by focusing only on settings management.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
import sqlite3
from flask import g

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('settings_service')


class SettingsService:
    """Service for managing application settings"""
    
    def __init__(self, db_path: str = 'instance/tokens.db'):
        """
        Initialize settings service
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_settings_table()
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """
        Get a database connection
        
        Returns:
            sqlite3.Connection: Database connection
        """
        # First check if we're in a Flask context and can use g
        try:
            if hasattr(g, 'db'):
                return g.db
        except RuntimeError:
            # Not in a Flask context, proceed with direct connection
            pass
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_settings_table(self) -> None:
        """Ensure the settings table exists in the database"""
        try:
            conn = self._get_db_connection()
            
            # Create printer_settings table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS printer_settings (
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Update trigger for updated_at
            conn.execute('''
                CREATE TRIGGER IF NOT EXISTS update_printer_settings_timestamp
                AFTER UPDATE ON printer_settings
                FOR EACH ROW
                BEGIN
                    UPDATE printer_settings SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = OLD.id;
                END
            ''')
            
            conn.commit()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
                
        except Exception as e:
            logger.error(f"Error ensuring settings table: {str(e)}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Any: Setting value or default
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM printer_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
            
            if row:
                # Try to parse as JSON, fall back to raw value
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            else:
                return default
                
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a setting value
        
        Args:
            key: Setting key
            value: Setting value (will be JSON-encoded if not a string)
            
        Returns:
            bool: True if successful
        """
        try:
            conn = self._get_db_connection()
            
            # Convert value to JSON string if not already a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            conn.execute(
                "INSERT INTO printer_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = ?",
                (key, value, value)
            )
            
            conn.commit()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
                
            logger.info(f"Setting {key} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {key}: {str(e)}")
            return False
    
    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting
        
        Args:
            key: Setting key
            
        Returns:
            bool: True if successful
        """
        try:
            conn = self._get_db_connection()
            
            conn.execute("DELETE FROM printer_settings WHERE key = ?", (key,))
            conn.commit()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
                
            logger.info(f"Setting {key} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting setting {key}: {str(e)}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings
        
        Returns:
            Dict[str, Any]: Dictionary of all settings
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT key, value FROM printer_settings")
            rows = cursor.fetchall()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
            
            settings = {}
            for row in rows:
                key = row['key']
                try:
                    settings[key] = json.loads(row['value'])
                except json.JSONDecodeError:
                    settings[key] = row['value']
            
            return settings
            
        except Exception as e:
            logger.error(f"Error getting all settings: {str(e)}")
            return {}
    
    def clear_all_settings(self) -> bool:
        """
        Clear all settings
        
        Returns:
            bool: True if successful
        """
        try:
            conn = self._get_db_connection()
            
            conn.execute("DELETE FROM printer_settings")
            conn.commit()
            
            # Close connection if not from Flask g
            if not hasattr(g, 'db'):
                conn.close()
                
            logger.info("All settings cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing all settings: {str(e)}")
            return False
    
    # Printer-specific settings methods
    def get_printer_config(self) -> Dict[str, Any]:
        """
        Get printer configuration
        
        Returns:
            Dict[str, Any]: Printer configuration dictionary
        """
        return self.get_setting('printer_config', {
            'printer_type': 'bluetooth',
            'bluetooth_address': None,
            'bluetooth_port': 1,
            'paper_width': 58
        })
    
    def save_printer_config(self, config: Dict[str, Any]) -> bool:
        """
        Save printer configuration
        
        Args:
            config: Printer configuration dictionary
            
        Returns:
            bool: True if successful
        """
        return self.set_setting('printer_config', config)
    
    def get_printer_history(self) -> List[Dict]:
        """
        Get printer connection history
        
        Returns:
            List[Dict]: List of previous printer connections
        """
        return self.get_setting('printer_history', [])
    
    def add_printer_to_history(self, printer_info: Dict) -> bool:
        """
        Add a printer to the connection history
        
        Args:
            printer_info: Dictionary with printer information
            
        Returns:
            bool: True if successful
        """
        history = self.get_printer_history()
        
        # Remove any existing entry with the same address
        history = [p for p in history if p.get('address') != printer_info.get('address')]
        
        # Add to the beginning of the list
        history.insert(0, printer_info)
        
        # Limit history to 10 items
        if len(history) > 10:
            history = history[:10]
        
        return self.set_setting('printer_history', history)
    
    def clear_printer_history(self) -> bool:
        """
        Clear printer connection history
        
        Returns:
            bool: True if successful
        """
        return self.set_setting('printer_history', [])
    
    def get_default_printer(self) -> Optional[Dict]:
        """
        Get default printer configuration
        
        Returns:
            Optional[Dict]: Default printer configuration or None
        """
        return self.get_setting('default_printer', None)
    
    def set_default_printer(self, printer_info: Dict) -> bool:
        """
        Set default printer
        
        Args:
            printer_info: Dictionary with printer information
            
        Returns:
            bool: True if successful
        """
        # Add to history as well
        self.add_printer_to_history(printer_info)
        
        # Set as default
        return self.set_setting('default_printer', printer_info)


# Factory function
def create_settings_service(db_path: str = None) -> SettingsService:
    """
    Factory function to create a settings service
    
    Args:
        db_path: Optional database path override
        
    Returns:
        SettingsService: Configured settings service
    """
    if db_path:
        return SettingsService(db_path)
    else:
        return SettingsService()