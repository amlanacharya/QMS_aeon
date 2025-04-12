/**
 * Android Bluetooth Bridge for POS Printing
 * 
 * This script provides a bridge between the web application and 
 * Android's native Bluetooth capabilities for printing.
 * 
 * It detects if running in an Android WebView with Bluetooth printing capability
 * and provides appropriate interfaces.
 */

class AndroidBluetoothBridge {
    constructor() {
        this.isAndroid = this._detectAndroid();
        this.hasNativeBridge = this._detectNativeBridge();
        this.isSupported = this.isAndroid && this.hasNativeBridge;
        this.printerAddress = null;
        this.deviceListeners = [];
        this.statusListeners = [];
        
        // Initialize if supported
        if (this.isSupported) {
            this._initializeBridge();
        }
    }
    
    /**
     * Detect if running on Android
     */
    _detectAndroid() {
        const userAgent = navigator.userAgent.toLowerCase();
        return /android/.test(userAgent);
    }
    
    /**
     * Detect if native bridge is available
     */
    _detectNativeBridge() {
        return typeof window.AndroidBTPrinter !== 'undefined';
    }
    
    /**
     * Initialize the bridge
     */
    _initializeBridge() {
        // Set up callbacks for Android to call
        window.onBluetoothDeviceFound = this._handleDeviceFound.bind(this);
        window.onBluetoothStatusChanged = this._handleStatusChanged.bind(this);
        window.onBluetoothError = this._handleError.bind(this);
        
        console.log('Android Bluetooth Bridge initialized');
        
        // Check if a printer is already connected/saved
        this._loadSavedPrinter();
    }
    
    /**
     * Load any saved printer from Android
     */
    _loadSavedPrinter() {
        if (this.isSupported && window.AndroidBTPrinter.getSavedPrinter) {
            try {
                const printerJson = window.AndroidBTPrinter.getSavedPrinter();
                if (printerJson) {
                    const printer = JSON.parse(printerJson);
                    this.printerAddress = printer.address || null;
                    
                    // Notify listeners
                    this._notifyStatusListeners({
                        status: 'saved_printer',
                        printer: printer
                    });
                }
            } catch (e) {
                console.error('Error loading saved printer:', e);
            }
        }
    }
    
    /**
     * Handle device found callback from Android
     */
    _handleDeviceFound(deviceJson) {
        try {
            const device = JSON.parse(deviceJson);
            this._notifyDeviceListeners(device);
        } catch (e) {
            console.error('Error handling device found:', e);
        }
    }
    
    /**
     * Handle status change callback from Android
     */
    _handleStatusChanged(statusJson) {
        try {
            const status = JSON.parse(statusJson);
            this._notifyStatusListeners(status);
        } catch (e) {
            console.error('Error handling status changed:', e);
        }
    }
    
    /**
     * Handle error callback from Android
     */
    _handleError(errorJson) {
        try {
            const error = JSON.parse(errorJson);
            console.error('Bluetooth error:', error);
            
            this._notifyStatusListeners({
                status: 'error',
                error: error
            });
        } catch (e) {
            console.error('Error handling Bluetooth error:', e);
        }
    }
    
    /**
     * Notify device listeners
     */
    _notifyDeviceListeners(device) {
        for (const listener of this.deviceListeners) {
            try {
                listener(device);
            } catch (e) {
                console.error('Error in device listener:', e);
            }
        }
    }
    
    /**
     * Notify status listeners
     */
    _notifyStatusListeners(status) {
        for (const listener of this.statusListeners) {
            try {
                listener(status);
            } catch (e) {
                console.error('Error in status listener:', e);
            }
        }
    }
    
    /**
     * Start scanning for Bluetooth devices
     */
    startScan() {
        if (!this.isSupported) {
            return false;
        }
        
        try {
            window.AndroidBTPrinter.startScan();
            return true;
        } catch (e) {
            console.error('Error starting scan:', e);
            return false;
        }
    }
    
    /**
     * Stop scanning for Bluetooth devices
     */
    stopScan() {
        if (!this.isSupported) {
            return false;
        }
        
        try {
            window.AndroidBTPrinter.stopScan();
            return true;
        } catch (e) {
            console.error('Error stopping scan:', e);
            return false;
        }
    }
    
    /**
     * Connect to a Bluetooth printer
     */
    connectPrinter(address) {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Set up a one-time listener for connection result
                const connectionListener = (status) => {
                    if (status.status === 'connected' && status.address === address) {
                        // Connection successful
                        this.printerAddress = address;
                        this.statusListeners = this.statusListeners.filter(l => l !== connectionListener);
                        resolve(status);
                    } else if (status.status === 'error' && status.operation === 'connect') {
                        // Connection failed
                        this.statusListeners = this.statusListeners.filter(l => l !== connectionListener);
                        reject(new Error(status.message || 'Connection failed'));
                    }
                };
                
                this.statusListeners.push(connectionListener);
                
                // Add a timeout to remove the listener
                setTimeout(() => {
                    this.statusListeners = this.statusListeners.filter(l => l !== connectionListener);
                    reject(new Error('Connection timeout'));
                }, 30000); // 30-second timeout
                
                // Start connection
                window.AndroidBTPrinter.connectPrinter(address);
            } catch (e) {
                reject(e);
            }
        });
    }
    
    /**
     * Disconnect from the current printer
     */
    disconnectPrinter() {
        if (!this.isSupported || !this.printerAddress) {
            return Promise.reject(new Error('No printer connected'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Set up a one-time listener for disconnection result
                const disconnectionListener = (status) => {
                    if (status.status === 'disconnected') {
                        // Disconnection successful
                        this.printerAddress = null;
                        this.statusListeners = this.statusListeners.filter(l => l !== disconnectionListener);
                        resolve(status);
                    } else if (status.status === 'error' && status.operation === 'disconnect') {
                        // Disconnection failed
                        this.statusListeners = this.statusListeners.filter(l => l !== disconnectionListener);
                        reject(new Error(status.message || 'Disconnection failed'));
                    }
                };
                
                this.statusListeners.push(disconnectionListener);
                
                // Add a timeout to remove the listener
                setTimeout(() => {
                    this.statusListeners = this.statusListeners.filter(l => l !== disconnectionListener);
                    reject(new Error('Disconnection timeout'));
                }, 5000); // 5-second timeout
                
                // Start disconnection
                window.AndroidBTPrinter.disconnectPrinter();
            } catch (e) {
                reject(e);
            }
        });
    }
    
    /**
     * Print a receipt from an HTML template
     */
    printReceipt(html) {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        if (!this.printerAddress) {
            return Promise.reject(new Error('No printer connected'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Set up a one-time listener for print result
                const printListener = (status) => {
                    if (status.status === 'printed') {
                        // Print successful
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        resolve(status);
                    } else if (status.status === 'error' && status.operation === 'print') {
                        // Print failed
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        reject(new Error(status.message || 'Print failed'));
                    }
                };
                
                this.statusListeners.push(printListener);
                
                // Add a timeout to remove the listener
                setTimeout(() => {
                    this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                    reject(new Error('Print timeout'));
                }, 15000); // 15-second timeout
                
                // Start printing
                window.AndroidBTPrinter.printHtml(html);
            } catch (e) {
                reject(e);
            }
        });
    }
    
    /**
     * Print a receipt for a token directly
     */
    printToken(tokenId) {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        if (!this.printerAddress) {
            return Promise.reject(new Error('No printer connected'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Set up a one-time listener for print result
                const printListener = (status) => {
                    if (status.status === 'printed') {
                        // Print successful
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        resolve(status);
                    } else if (status.status === 'error' && status.operation === 'print') {
                        // Print failed
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        reject(new Error(status.message || 'Print failed'));
                    }
                };
                
                this.statusListeners.push(printListener);
                
                // Add a timeout to remove the listener
                setTimeout(() => {
                    this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                    reject(new Error('Print timeout'));
                }, 15000); // 15-second timeout
                
                // Start printing
                window.AndroidBTPrinter.printToken(tokenId.toString());
            } catch (e) {
                reject(e);
            }
        });
    }
    
    /**
     * Print a test page
     */
    printTestPage() {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        if (!this.printerAddress) {
            return Promise.reject(new Error('No printer connected'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Set up a one-time listener for print result
                const printListener = (status) => {
                    if (status.status === 'printed') {
                        // Print successful
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        resolve(status);
                    } else if (status.status === 'error' && status.operation === 'print') {
                        // Print failed
                        this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                        reject(new Error(status.message || 'Print failed'));
                    }
                };
                
                this.statusListeners.push(printListener);
                
                // Add a timeout to remove the listener
                setTimeout(() => {
                    this.statusListeners = this.statusListeners.filter(l => l !== printListener);
                    reject(new Error('Print timeout'));
                }, 15000); // 15-second timeout
                
                // Start printing
                window.AndroidBTPrinter.printTestPage();
            } catch (e) {
                reject(e);
            }
        });
    }
    
    /**
     * Check if Bluetooth is enabled
     */
    isBluetoothEnabled() {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        try {
            return Promise.resolve(window.AndroidBTPrinter.isBluetoothEnabled());
        } catch (e) {
            return Promise.reject(e);
        }
    }
    
    /**
     * Request to enable Bluetooth
     */
    requestEnableBluetooth() {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        try {
            window.AndroidBTPrinter.requestEnableBluetooth();
            return Promise.resolve(true);
        } catch (e) {
            return Promise.reject(e);
        }
    }
    
    /**
     * Get information about the current connection
     */
    getConnectionInfo() {
        if (!this.isSupported) {
            return Promise.reject(new Error('Native Bluetooth not supported'));
        }
        
        try {
            const infoJson = window.AndroidBTPrinter.getConnectionInfo();
            return Promise.resolve(JSON.parse(infoJson));
        } catch (e) {
            return Promise.reject(e);
        }
    }
    
    /**
     * Add device found listener
     */
    onDeviceFound(listener) {
        this.deviceListeners.push(listener);
        return () => {
            this.deviceListeners = this.deviceListeners.filter(l => l !== listener);
        };
    }
    
    /**
     * Add status change listener
     */
    onStatusChanged(listener) {
        this.statusListeners.push(listener);
        return () => {
            this.statusListeners = this.statusListeners.filter(l => l !== listener);
        };
    }
}

// Create global instance
window.bluetoothPrinter = new AndroidBluetoothBridge();

// Add convenience function for token printing
function printTokenWithBluetooth(tokenId) {
    // Check if native Android Bluetooth is available
    if (window.bluetoothPrinter && window.bluetoothPrinter.isSupported) {
        // Try to print using native Android
        return window.bluetoothPrinter.printToken(tokenId)
            .then(() => {
                console.log('Token printed successfully via Android Bluetooth');
                return { success: true };
            })
            .catch(error => {
                console.error('Error printing via Android Bluetooth:', error);
                
                // If not connected, show connection dialog
                if (error.message && (
                    error.message.includes('No printer connected') || 
                    error.message.includes('not connected')
                )) {
                    // Show printer selection dialog
                    showPrinterSelectionDialog();
                }
                
                return { 
                    success: false, 
                    error: error.message || 'Printing failed',
                    fallback: true
                };
            });
    } else {
        // Fall back to server-side printing
        return Promise.resolve({
            success: false,
            fallback: true,
            error: 'Native Bluetooth not supported'
        });
    }
}

// Function to show printer selection dialog (to be implemented in the app)
function showPrinterSelectionDialog() {
    // This function would be implemented to show a UI for printer selection
    console.log('Showing printer selection dialog');
    
    // For now, just show an alert
    alert('Please connect to a Bluetooth printer in the printer settings page.');
}

// Add initialization check when the page loads
document.addEventListener('DOMContentLoaded', function() {
    if (window.bluetoothPrinter && window.bluetoothPrinter.isSupported) {
        console.log('Android Bluetooth printing is available');
        
        // Add a class to the body for CSS targeting
        document.body.classList.add('android-bt-printing');
        
        // Check if Bluetooth is enabled
        window.bluetoothPrinter.isBluetoothEnabled()
            .then(enabled => {
                if (!enabled) {
                    console.log('Bluetooth is disabled, requesting to enable');
                    window.bluetoothPrinter.requestEnableBluetooth();
                }
            })
            .catch(error => {
                console.error('Error checking Bluetooth status:', error);
            });
    } else {
        console.log('Android Bluetooth printing is not available');
    }
});