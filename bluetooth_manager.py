# bluetooth_manager.py
"""
Bluetooth discovery and management module for finding and connecting to Bluetooth printers.
This follows the Single Responsibility Principle by focusing only on Bluetooth operations.
"""
import logging
from typing import List, Dict, Optional, Union, Tuple
import json
import re
import os
import subprocess
import platform
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bluetooth_manager')


class BluetoothDevice:
    """Class representing a discovered Bluetooth device"""
    def __init__(self, address: str, name: str = None, rssi: int = None, device_class: int = None):
        """
        Initialize a Bluetooth device
        
        Args:
            address: MAC address of the device
            name: Device name
            rssi: Signal strength
            device_class: Bluetooth device class (can be used to identify printers)
        """
        self.address = address
        self.name = name or "Unknown"
        self.rssi = rssi
        self.device_class = device_class
        
    def __str__(self) -> str:
        return f"{self.name} ({self.address})"
    
    def to_dict(self) -> Dict:
        """Convert device to dictionary for JSON serialization"""
        return {
            'address': self.address,
            'name': self.name,
            'rssi': self.rssi,
            'device_class': self.device_class,
            'is_printer': self.is_printer()
        }
    
    def is_printer(self) -> bool:
        """
        Check if this device is likely a printer based on its name or class
        
        Returns:
            bool: True if the device is likely a printer
        """
        if not self.name:
            return False
            
        printer_keywords = ['print', 'pos', 'escpos', 'thermal', 'receipt']
        name_lower = self.name.lower()
        
        # Check if any printer keywords are in the name
        for keyword in printer_keywords:
            if keyword in name_lower:
                return True
        
        # Check device class if available
        # 0x0680 is the class for "Imaging:Printer"
        if self.device_class and (self.device_class & 0x0680) == 0x0680:
            return True
            
        return False


class BluetoothManager:
    """Class for discovering and managing Bluetooth devices"""
    
    def __init__(self):
        """Initialize Bluetooth manager"""
        self._system = platform.system().lower()
        self._last_devices: List[BluetoothDevice] = []
        self._is_scanning = False
    
    def check_bluetooth_available(self) -> bool:
        """
        Check if Bluetooth is available on this system
        
        Returns:
            bool: True if Bluetooth is available
        """
        try:
            if self._system == 'linux':
                # Check if hcitool is available
                result = subprocess.run(['which', 'hcitool'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
                return result.returncode == 0
            elif self._system == 'darwin':  # macOS
                # Check if system_profiler is available
                result = subprocess.run(['system_profiler', 'SPBluetoothDataType'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
                return result.returncode == 0
            elif self._system == 'windows':
                # Simple check for Windows - this is approximate
                try:
                    import wmi
                    c = wmi.WMI()
                    bluetooth_devices = c.Win32_PnPEntity(PNPClass="Bluetooth")
                    return len(bluetooth_devices) > 0
                except ImportError:
                    logger.warning("WMI module not available for Windows Bluetooth check")
                    # Fallback check using PowerShell
                    cmd = ['powershell', '-Command', 
                           "Get-PnpDevice -Class Bluetooth | Select-Object Status"]
                    result = subprocess.run(cmd, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
                    return 'OK' in result.stdout.decode('utf-8')
            else:
                logger.warning(f"Unsupported operating system: {self._system}")
                return False
        except Exception as e:
            logger.error(f"Error checking Bluetooth availability: {str(e)}")
            return False
    
    def discover_devices(self, timeout: int = 10) -> List[BluetoothDevice]:
        """
        Discover nearby Bluetooth devices
        
        Args:
            timeout: Timeout in seconds for discovery
            
        Returns:
            List[BluetoothDevice]: List of discovered devices
        """
        if self._is_scanning:
            logger.warning("Scan already in progress, returning last results")
            return self._last_devices
            
        self._is_scanning = True
        devices = []
        
        try:
            # Platform-specific discovery implementation
            if self._system == 'linux':
                devices = self._discover_linux(timeout)
            elif self._system == 'darwin':  # macOS
                devices = self._discover_macos(timeout)
            elif self._system == 'windows':
                devices = self._discover_windows(timeout)
            else:
                logger.warning(f"Bluetooth discovery not implemented for {self._system}")
            
            # Sort devices by signal strength if available
            devices.sort(key=lambda d: d.rssi if d.rssi is not None else -999, reverse=True)
            
            self._last_devices = devices
            return devices
            
        except Exception as e:
            logger.error(f"Error discovering Bluetooth devices: {str(e)}")
            return []
        finally:
            self._is_scanning = False
    
    def _discover_linux(self, timeout: int) -> List[BluetoothDevice]:
        """
        Discover Bluetooth devices on Linux
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            List[BluetoothDevice]: Discovered devices
        """
        devices = []
        
        try:
            # Try using bluetoothctl (more modern)
            subprocess.run(['bluetoothctl', 'scan', 'on'], 
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,
                          timeout=timeout)
                          
            # Get device list
            output = subprocess.check_output(['bluetoothctl', 'devices'])
            lines = output.decode('utf-8').strip().split('\n')
            
            for line in lines:
                if not line:
                    continue
                # Parse "Device XX:XX:XX:XX:XX:XX DeviceName"
                match = re.match(r'Device\s+([0-9A-F:]{17})\s+(.*)', line)
                if match:
                    addr = match.group(1)
                    name = match.group(2)
                    devices.append(BluetoothDevice(address=addr, name=name))
            
            # Fall back to hcitool if no devices found
            if not devices:
                logger.info("Falling back to hcitool for device discovery")
                # Scan for devices
                subprocess.run(['hcitool', 'scan', '--flush'], 
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              timeout=timeout)
                
                # Get device list
                output = subprocess.check_output(['hcitool', 'scan'])
                lines = output.decode('utf-8').strip().split('\n')[1:]  # Skip header
                
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        addr = parts[1]
                        name = parts[2] if len(parts) > 2 else "Unknown"
                        devices.append(BluetoothDevice(address=addr, name=name))
        
        except Exception as e:
            logger.error(f"Error discovering devices on Linux: {str(e)}")
            
        return devices
    
    def _discover_macos(self, timeout: int) -> List[BluetoothDevice]:
        """
        Discover Bluetooth devices on macOS
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            List[BluetoothDevice]: Discovered devices
        """
        devices = []
        
        try:
            # Use system_profiler to get Bluetooth devices
            output = subprocess.check_output(['system_profiler', 'SPBluetoothDataType'])
            text = output.decode('utf-8')
            
            # Parse the system_profiler output
            sections = text.split("Bluetooth:")
            if len(sections) > 1:
                bt_section = sections[1]
                
                # Find device entries
                device_sections = re.findall(r'(\S[^\n]+):\s+[^\n]*\s+Address: ([0-9A-F:]{17})', bt_section)
                
                for name, addr in device_sections:
                    name = name.strip()
                    addr = addr.strip()
                    devices.append(BluetoothDevice(address=addr, name=name))
        
        except Exception as e:
            logger.error(f"Error discovering devices on macOS: {str(e)}")
            
        return devices
    
    def _discover_windows(self, timeout: int) -> List[BluetoothDevice]:
        """
        Discover Bluetooth devices on Windows
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            List[BluetoothDevice]: Discovered devices
        """
        devices = []
        
        try:
            # Try using WMI if available
            try:
                import wmi
                c = wmi.WMI()
                bluetooth_devices = c.Win32_PnPEntity(PNPClass="Bluetooth")
                
                for device in bluetooth_devices:
                    name = device.Caption or device.Description or "Unknown"
                    # Extract MAC from device ID if available
                    addr = "Unknown"
                    if hasattr(device, 'PNPDeviceID'):
                        match = re.search(r'_([0-9A-F]{12})&', device.PNPDeviceID)
                        if match:
                            mac = match.group(1)
                            addr = ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
                    
                    devices.append(BluetoothDevice(address=addr, name=name))
                    
                return devices
            
            except ImportError:
                logger.warning("WMI module not available, falling back to PowerShell")
            
            # Fallback to PowerShell
            cmd = ['powershell', '-Command', 
                  "Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, DeviceID | ConvertTo-Json"]
            result = subprocess.run(cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=timeout)
            
            data = json.loads(result.stdout.decode('utf-8'))
            
            # PowerShell may return a single object or an array
            if not isinstance(data, list):
                data = [data]
                
            for device in data:
                name = device.get('FriendlyName', 'Unknown')
                device_id = device.get('DeviceID', '')
                
                # Extract MAC from device ID if available
                addr = "Unknown"
                match = re.search(r'_([0-9A-F]{12})&', device_id)
                if match:
                    mac = match.group(1)
                    addr = ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
                
                devices.append(BluetoothDevice(address=addr, name=name))
        
        except Exception as e:
            logger.error(f"Error discovering devices on Windows: {str(e)}")
            
        return devices
    
    def get_printer_devices(self) -> List[BluetoothDevice]:
        """
        Get devices that are likely printers from the last scan
        
        Returns:
            List[BluetoothDevice]: List of devices that are likely printers
        """
        return [device for device in self._last_devices if device.is_printer()]
    
    def check_device_available(self, address: str) -> bool:
        """
        Check if a specific device is available/reachable
        
        Args:
            address: Device MAC address
            
        Returns:
            bool: True if device is available
        """
        if not address:
            return False
            
        try:
            if self._system == 'linux':
                # Use l2ping to check device availability
                result = subprocess.run(['l2ping', '-c', '1', address], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      timeout=5)
                return result.returncode == 0
            elif self._system == 'darwin':  # macOS
                # macOS doesn't have a built-in tool for direct Bluetooth ping
                # Check if device is in the known devices list
                return any(d.address == address for d in self._discover_macos(5))
            elif self._system == 'windows':
                # Windows doesn't have a built-in tool for direct Bluetooth ping
                # Check if device is in the known devices list
                return any(d.address == address for d in self._discover_windows(5))
            else:
                logger.warning(f"Device availability check not implemented for {self._system}")
                return False
        except Exception as e:
            logger.error(f"Error checking device availability: {str(e)}")
            return False
    
    def pair_device(self, address: str, pin: str = None) -> bool:
        """
        Attempt to pair with a device
        
        Args:
            address: Device MAC address
            pin: PIN code for pairing (if required)
            
        Returns:
            bool: True if pairing successful or already paired
        """
        if not address:
            return False
            
        try:
            if self._system == 'linux':
                # Use bluetoothctl to pair
                if pin:
                    # Set PIN first
                    subprocess.run(['bluetoothctl', 'agent', 'on'], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
                    # Create PIN authorization script
                    echo_cmd = f'echo -e "agent on\\ndefault-agent\\n{pin}\\npair {address}\\ntrust {address}\\nquit" | bluetoothctl'
                    result = subprocess.run(echo_cmd, 
                                          shell=True,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          timeout=20)
                else:
                    # Try pairing without PIN
                    result = subprocess.run(['bluetoothctl', 'pair', address], 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          timeout=20)
                return "successful" in result.stdout.decode('utf-8').lower() or "already paired" in result.stdout.decode('utf-8').lower()
            else:
                logger.warning(f"Pairing not directly implemented for {self._system}")
                logger.info("This operation typically requires manual pairing through the OS interface")
                return False
        except Exception as e:
            logger.error(f"Error pairing with device: {str(e)}")
            return False
    
    def get_system_info(self) -> Dict:
        """
        Get information about the system's Bluetooth capabilities
        
        Returns:
            Dict: System information
        """
        info = {
            'system': self._system,
            'bluetooth_available': self.check_bluetooth_available(),
            'implementation': 'native'
        }
        
        try:
            if self._system == 'linux':
                # Get adapter information
                result = subprocess.run(['hciconfig'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
                info['adapter_info'] = result.stdout.decode('utf-8')
            elif self._system == 'darwin':
                # Get macOS Bluetooth info
                result = subprocess.run(['system_profiler', 'SPBluetoothDataType'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
                info['adapter_info'] = result.stdout.decode('utf-8')
            elif self._system == 'windows':
                # Get Windows Bluetooth info via PowerShell
                cmd = ['powershell', '-Command', 
                      "Get-PnpDevice -Class Bluetooth | Select-Object Status, FriendlyName | ConvertTo-Json"]
                result = subprocess.run(cmd, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
                info['adapter_info'] = result.stdout.decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            info['error'] = str(e)
            
        return info


# Factory function to create the bluetooth manager
def create_bluetooth_manager() -> BluetoothManager:
    """
    Factory function to create a Bluetooth manager instance
    
    Returns:
        BluetoothManager: Bluetooth manager instance
    """
    return BluetoothManager()