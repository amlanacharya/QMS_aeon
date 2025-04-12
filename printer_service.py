# printer_service.py
"""
Printer service module for handling ESC/POS printing operations.
This module follows the Single Responsibility Principle by focusing only on printer-related tasks.
"""
from escpos.printer import Usb, Network, Serial
# Note: Bluetooth is not directly available in python-escpos
# We'll implement custom Bluetooth functionality
import socket
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import logging
from datetime import datetime
import re
from typing import Dict, Optional, Union, Tuple, List
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('printer_service')


# Custom Bluetooth implementation for ESC/POS
class Bluetooth:
    """Custom Bluetooth implementation for ESC/POS"""
    
    def __init__(self, mac_address, port=1):
        """
        Initialize Bluetooth printer
        
        Args:
            mac_address: MAC address of the Bluetooth printer
            port: Bluetooth port (usually 1)
        """
        self.mac_address = mac_address
        self.port = port
        self.socket = None
        self.capabilities = {
            'barcode': True,
            'qr': True,
            'cut': True,
            'bitimage': True
        }
        
    def open(self):
        """Open Bluetooth connection"""
        try:
            self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.socket.connect((self.mac_address, self.port))
            logger.info(f"Connected to Bluetooth printer at {self.mac_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Bluetooth printer: {str(e)}")
            self.socket = None
            return False
            
    def close(self):
        """Close Bluetooth connection"""
        if self.socket:
            try:
                self.socket.close()
                logger.info("Bluetooth connection closed")
            except Exception as e:
                logger.error(f"Error closing Bluetooth connection: {str(e)}")
            self.socket = None
            
    def _raw(self, data):
        """Send raw data to printer"""
        if not self.socket:
            if not self.open():
                raise Exception("Printer not connected")
                
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            self.socket.send(data)
        except Exception as e:
            logger.error(f"Error sending data to printer: {str(e)}")
            self.close()
            raise
            
    # Implement basic ESC/POS commands
    def text(self, text):
        """Print text"""
        self._raw(text)
        
    def set_align(self, align):
        """Set text alignment"""
        if align == "center":
            self._raw(b'\x1b\x61\x01')
        elif align == "right":
            self._raw(b'\x1b\x61\x02')
        else:  # left
            self._raw(b'\x1b\x61\x00')
            
    def set_text_size(self, width="normal", height="normal"):
        """Set text size"""
        sizes = {
            "normal": 0,
            "2x": 1,
            "3x": 2,
            "4x": 3
        }
        w = sizes.get(width, 0)
        h = sizes.get(height, 0)
        size = (w << 4) | h
        self._raw(f"\x1d\x21{chr(size)}".encode('latin-1'))
        
    def cut(self):
        """Cut paper"""
        self._raw(b'\x1d\x56\x41\x00')
        
    def qr(self, data, size=8):
        """Print QR code"""
        # Generate QR code using qrcode library
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        width, height = qr_img.size
        
        # Convert to bitmap and send to printer
        self._raw(b'\x1d\x76\x30\x00')  # Set raster bit-image mode
        self._raw(bytes([width & 0xff, (width >> 8) & 0xff, height & 0xff, (height >> 8) & 0xff]))
        
        pixels = qr_img.load()
        for y in range(height):
            line = bytearray()
            for x in range(0, width, 8):
                byte = 0
                for b in range(min(8, width - x)):
                    if pixels[x + b, y] == 0:  # Black is usually 0 in PIL
                        byte |= (1 << (7 - b))
                line.append(byte)
            self._raw(bytes(line))
            

class PrinterConfig:
    """Configuration class for printer settings"""
    def __init__(self, 
                printer_type: str = 'bluetooth',
                bluetooth_address: str = None, 
                bluetooth_port: int = 1,
                usb_vendor_id: int = None,
                usb_product_id: int = None,
                network_ip: str = None,
                network_port: int = 9100,
                serial_port: str = None,
                serial_baudrate: int = 9600,
                paper_width: int = 58):
        """
        Initialize printer configuration
        
        Args:
            printer_type: Type of printer connection ('bluetooth', 'usb', 'network', 'serial')
            bluetooth_address: MAC address for Bluetooth printer
            bluetooth_port: Port for Bluetooth printer (usually 1)
            usb_vendor_id: USB vendor ID
            usb_product_id: USB product ID
            network_ip: IP address for network printer
            network_port: Port for network printer
            serial_port: Serial port path
            serial_baudrate: Serial baudrate
            paper_width: Paper width in mm (typically 58, 80)
        """
        self.printer_type = printer_type
        self.bluetooth_address = bluetooth_address
        self.bluetooth_port = bluetooth_port
        self.usb_vendor_id = usb_vendor_id
        self.usb_product_id = usb_product_id
        self.network_ip = network_ip
        self.network_port = network_port
        self.serial_port = serial_port
        self.serial_baudrate = serial_baudrate
        self.paper_width = paper_width
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'PrinterConfig':
        """Create a PrinterConfig instance from a dictionary"""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict:
        """Convert configuration to a dictionary"""
        return {
            'printer_type': self.printer_type,
            'bluetooth_address': self.bluetooth_address,
            'bluetooth_port': self.bluetooth_port,
            'usb_vendor_id': self.usb_vendor_id,
            'usb_product_id': self.usb_product_id,
            'network_ip': self.network_ip,
            'network_port': self.network_port,
            'serial_port': self.serial_port,
            'serial_baudrate': self.serial_baudrate,
            'paper_width': self.paper_width
        }


class PrinterService:
    """Service class for printer operations following the Dependency Inversion Principle"""
    
    def __init__(self, config: PrinterConfig = None):
        """
        Initialize the printer service
        
        Args:
            config: PrinterConfig object with printer settings
        """
        self.config = config or PrinterConfig()
        self._printer = None
    
    def connect(self) -> bool:
        """
        Connect to the printer based on the configured connection type
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.config.printer_type == 'bluetooth':
                if not self.config.bluetooth_address:
                    logger.error("Bluetooth address not provided")
                    return False
                self._printer = Bluetooth(
                    self.config.bluetooth_address,
                    self.config.bluetooth_port
                )
                # Try to open the connection
                return self._printer.open()
                
            elif self.config.printer_type == 'usb':
                if not self.config.usb_vendor_id or not self.config.usb_product_id:
                    logger.error("USB vendor ID or product ID not provided")
                    return False
                self._printer = Usb(
                    self.config.usb_vendor_id,
                    self.config.usb_product_id
                )
                return True
                
            elif self.config.printer_type == 'network':
                if not self.config.network_ip:
                    logger.error("Network IP not provided")
                    return False
                self._printer = Network(
                    self.config.network_ip,
                    self.config.network_port
                )
                return True
                
            elif self.config.printer_type == 'serial':
                if not self.config.serial_port:
                    logger.error("Serial port not provided")
                    return False
                self._printer = Serial(
                    self.config.serial_port,
                    self.config.serial_baudrate
                )
                return True
                
            else:
                logger.error(f"Unsupported printer type: {self.config.printer_type}")
                return False
            
            logger.info(f"Successfully connected to {self.config.printer_type} printer")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to printer: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Close the printer connection if it exists"""
        if self._printer:
            try:
                # Some printer connections need to be closed explicitly
                if hasattr(self._printer, 'close'):
                    self._printer.close()
                self._printer = None
                logger.info("Printer disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting printer: {str(e)}")
    
    def print_token(self, 
                   token_number: str, 
                   customer_name: str = "", 
                   application_number: str = "", 
                   phone_number: str = "", 
                   created_at: datetime = None,
                   include_qr: bool = True) -> bool:
        """
        Print a token receipt
        
        Args:
            token_number: The token identifier
            customer_name: Customer's name
            application_number: Application reference number
            phone_number: Customer's phone number
            created_at: Token creation timestamp
            include_qr: Whether to include a QR code
            
        Returns:
            bool: True if printing successful, False otherwise
        """
        if not self._printer:
            success = self.connect()
            if not success:
                return False
                
        try:
            # Calculate timestamp
            timestamp = created_at or datetime.now()
            time_str = timestamp.strftime('%Y-%m-%d %H:%M')
            
            # Configure based on paper width
            if self.config.paper_width >= 80:
                title_size = "2x"
                token_size = "3x"
            else:
                title_size = "normal"
                token_size = "2x"
            
            # Print header
            self._printer.set_align("center")
            self._printer.text("Token Receipt\n")
            self._printer.text("------------------------\n")
            
            # Print token number
            self._printer.set_text_size(width=token_size, height=token_size)
            self._printer.text(f"{token_number}\n")
            self._printer.set_text_size()
            self._printer.text("\n")
            
            # Print customer details
            self._printer.set_align("left")
            if customer_name:
                self._printer.text(f"Name: {customer_name}\n")
            if application_number:
                self._printer.text(f"App No: {application_number}\n")
            if phone_number:
                self._printer.text(f"Phone: {phone_number}\n")
            
            self._printer.text(f"Time: {time_str}\n")
            
            # Add QR code if requested
            if include_qr:
                qr_data = f"TKN:{token_number}"
                self._printer.set_align("center")
                self._printer.qr(qr_data, size=8)
            
            # Print footer
            self._printer.set_align("center")
            self._printer.text("------------------------\n")
            self._printer.text("Please wait for your number\n")
            self._printer.text("to be called\n")
            self._printer.text("Thank you for your patience!\n\n\n")
            
            # Cut paper if available
            if hasattr(self._printer, 'cut'):
                self._printer.cut()
            
            logger.info(f"Successfully printed token: {token_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error printing token: {str(e)}")
            return False
    
    def print_test_page(self) -> bool:
        """
        Print a test page to verify printer connection
        
        Returns:
            bool: True if printing successful, False otherwise
        """
        if not self._printer:
            success = self.connect()
            if not success:
                return False
                
        try:
            self._printer.set_align("center")
            self._printer.text("TEST PAGE\n")
            self._printer.text("------------------------\n")
            self._printer.text("Printer is working correctly\n")
            self._printer.text(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._printer.text("------------------------\n\n\n")
            
            if hasattr(self._printer, 'cut'):
                self._printer.cut()
                
            logger.info("Successfully printed test page")
            return True
            
        except Exception as e:
            logger.error(f"Error printing test page: {str(e)}")
            return False
    
    def get_printer_status(self) -> Dict:
        """
        Get printer status information
        
        Returns:
            Dict: Printer status information
        """
        status = {
            'connected': self._printer is not None,
            'type': self.config.printer_type,
            'error': None
        }
        
        if not self._printer:
            status['error'] = "Printer not connected"
            return status
            
        try:
            # Try to query printer status (specific implementations may vary)
            # This is a basic implementation
            status['online'] = True
            return status
            
        except Exception as e:
            status['online'] = False
            status['error'] = str(e)
            return status


# Simple factory function for creating printer service instances
def create_printer_service(config_dict: Dict = None) -> PrinterService:
    """
    Factory function to create a properly configured printer service
    
    Args:
        config_dict: Dictionary with printer configuration
        
    Returns:
        PrinterService: Configured printer service instance
    """
    if config_dict:
        config = PrinterConfig.from_dict(config_dict)
    else:
        config = PrinterConfig()
    
    return PrinterService(config)