# printer_api.py
"""
API endpoints for printer management and operations.
This module provides the RESTful interface for printer functionality.
"""
from flask import Blueprint, request, jsonify, current_app, abort
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional, Any

from printer_service import create_printer_service, PrinterConfig
from bluetooth_manager import create_bluetooth_manager
from settings_service import create_settings_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('printer_api')

# Create Blueprint
printer_bp = Blueprint('printer', __name__, url_prefix='/api/printer')

# Create services
settings_service = create_settings_service()
bluetooth_manager = create_bluetooth_manager()


@printer_bp.route('/status', methods=['GET'])
def get_status():
    """Get printer status"""
    try:
        # Get printer config from settings
        printer_config = settings_service.get_printer_config()
        
        # Check if we have a printer configured
        if not printer_config.get('bluetooth_address'):
            return jsonify({
                'status': 'not_configured',
                'message': 'Printer not configured',
                'config': printer_config
            })
        
        # Create printer service with the stored config
        printer_service = create_printer_service(printer_config)
        
        # Try to connect
        connected = printer_service.connect()
        
        if connected:
            # Get printer status
            status = printer_service.get_printer_status()
            printer_service.disconnect()
            
            return jsonify({
                'status': 'connected',
                'printer_status': status,
                'config': printer_config
            })
        else:
            # Check if Bluetooth device is available
            bt_available = bluetooth_manager.check_device_available(
                printer_config.get('bluetooth_address')
            )
            
            return jsonify({
                'status': 'disconnected',
                'device_available': bt_available,
                'message': 'Could not connect to printer',
                'config': printer_config
            })
    except Exception as e:
        logger.error(f"Error getting printer status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/discover', methods=['GET'])
def discover_printers():
    """Discover Bluetooth printers"""
    try:
        # Check if Bluetooth is available
        if not bluetooth_manager.check_bluetooth_available():
            return jsonify({
                'status': 'error',
                'message': 'Bluetooth not available on this system'
            }), 400
        
        # Get timeout parameter (default 10 seconds)
        timeout = int(request.args.get('timeout', 10))
        
        # Discover devices
        devices = bluetooth_manager.discover_devices(timeout)
        
        # Convert devices to dict for JSON serialization
        device_list = [device.to_dict() for device in devices]
        
        # Get printer devices
        printer_devices = [device.to_dict() for device in bluetooth_manager.get_printer_devices()]
        
        return jsonify({
            'status': 'success',
            'devices': device_list,
            'printer_devices': printer_devices,
            'system_info': bluetooth_manager.get_system_info()
        })
    except Exception as e:
        logger.error(f"Error discovering printers: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/connect', methods=['POST'])
def connect_printer():
    """Connect to a specific printer"""
    try:
        data = request.json
        
        if not data or not data.get('address'):
            return jsonify({
                'status': 'error',
                'message': 'Printer address required'
            }), 400
        
        address = data.get('address')
        name = data.get('name', 'Unknown Printer')
        port = int(data.get('port', 1))
        paper_width = int(data.get('paper_width', 58))
        
        # Create printer configuration
        printer_config = {
            'printer_type': 'bluetooth',
            'bluetooth_address': address,
            'bluetooth_port': port,
            'paper_width': paper_width
        }
        
        # Create printer service
        printer_service = create_printer_service(printer_config)
        
        # Try to connect
        connected = printer_service.connect()
        
        if connected:
            # Save configuration
            settings_service.save_printer_config(printer_config)
            
            # Add to history
            settings_service.add_printer_to_history({
                'address': address,
                'name': name,
                'port': port,
                'paper_width': paper_width,
                'last_connected': datetime.now().isoformat()
            })
            
            # Set as default if requested
            if data.get('set_default', False):
                settings_service.set_default_printer({
                    'address': address,
                    'name': name,
                    'port': port,
                    'paper_width': paper_width
                })
            
            # Disconnect
            printer_service.disconnect()
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully connected to {name}',
                'config': printer_config
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to connect to printer'
            }), 400
    except Exception as e:
        logger.error(f"Error connecting to printer: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/print-test', methods=['POST'])
def print_test():
    """Print a test page"""
    try:
        # Get printer config from settings or request
        if request.json and request.json.get('config'):
            printer_config = request.json.get('config')
        else:
            printer_config = settings_service.get_printer_config()
        
        # Check if we have a printer configured
        if not printer_config.get('bluetooth_address'):
            return jsonify({
                'status': 'error',
                'message': 'Printer not configured'
            }), 400
        
        # Create printer service
        printer_service = create_printer_service(printer_config)
        
        # Print test page
        success = printer_service.print_test_page()
        
        # Disconnect
        printer_service.disconnect()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Test page printed successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to print test page'
            }), 400
    except Exception as e:
        logger.error(f"Error printing test page: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/print-token/<int:token_id>', methods=['POST'])
def print_token(token_id):
    """Print a specific token"""
    try:
        from app import Token  # Import here to avoid circular imports
        
        # Get token from database
        token = Token.query.get(token_id)
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': f'Token with ID {token_id} not found'
            }), 404
        
        # Get printer config from settings or request
        if request.json and request.json.get('config'):
            printer_config = request.json.get('config')
        else:
            printer_config = settings_service.get_printer_config()
        
        # Check if we have a printer configured
        if not printer_config.get('bluetooth_address'):
            return jsonify({
                'status': 'error',
                'message': 'Printer not configured'
            }), 400
        
        # Create printer service
        printer_service = create_printer_service(printer_config)
        
        # Print token
        success = printer_service.print_token(
            token_number=token.token_number,
            customer_name=token.customer_name,
            application_number=token.application_number,
            phone_number=token.phone_number,
            created_at=token.created_at,
            include_qr=True
        )
        
        # Disconnect
        printer_service.disconnect()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Token {token.token_number} printed successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to print token'
            }), 400
    except Exception as e:
        logger.error(f"Error printing token: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/settings', methods=['GET'])
def get_printer_settings():
    """Get printer settings"""
    try:
        # Get printer configuration
        printer_config = settings_service.get_printer_config()
        
        # Get printer history
        printer_history = settings_service.get_printer_history()
        
        # Get default printer
        default_printer = settings_service.get_default_printer()
        
        return jsonify({
            'status': 'success',
            'config': printer_config,
            'history': printer_history,
            'default_printer': default_printer
        })
    except Exception as e:
        logger.error(f"Error getting printer settings: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/settings', methods=['POST'])
def save_printer_settings():
    """Save printer settings"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Update printer configuration
        if 'config' in data:
            settings_service.save_printer_config(data['config'])
        
        # Update default printer
        if 'default_printer' in data:
            settings_service.set_default_printer(data['default_printer'])
        
        return jsonify({
            'status': 'success',
            'message': 'Printer settings saved successfully'
        })
    except Exception as e:
        logger.error(f"Error saving printer settings: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/history/clear', methods=['POST'])
def clear_printer_history():
    """Clear printer connection history"""
    try:
        settings_service.clear_printer_history()
        
        return jsonify({
            'status': 'success',
            'message': 'Printer history cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing printer history: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@printer_bp.route('/pair', methods=['POST'])
def pair_printer():
    """Pair with a Bluetooth printer"""
    try:
        data = request.json
        
        if not data or not data.get('address'):
            return jsonify({
                'status': 'error',
                'message': 'Printer address required'
            }), 400
        
        address = data.get('address')
        pin = data.get('pin')
        
        # Try to pair
        success = bluetooth_manager.pair_device(address, pin)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Printer paired successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to pair with printer'
            }), 400
    except Exception as e:
        logger.error(f"Error pairing with printer: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500