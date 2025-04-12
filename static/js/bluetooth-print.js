// static/js/bluetooth-print.js
class BluetoothPrinter {
    constructor() {
      this.device = null;
      this.characteristic = null;
    }
  
    async connect() {
      try {
        // Request the device with a printer service
        this.device = await navigator.bluetooth.requestDevice({
          filters: [
            { services: ['000018f0-0000-1000-8000-00805f9b34fb'] }, // Common printer service
            { namePrefix: 'Printer' },
            { namePrefix: 'BT' },
          ],
          optionalServices: ['battery_service', '0000ff00-0000-1000-8000-00805f9b34fb']
        });
  
        console.log('Device selected:', this.device.name);
        
        // Connect to the device
        const server = await this.device.gatt.connect();
        
        // Get the printer service
        const service = await server.getPrimaryService('0000ff00-0000-1000-8000-00805f9b34fb');
        
        // Get the characteristic for writing
        this.characteristic = await service.getCharacteristic('0000ff02-0000-1000-8000-00805f9b34fb');
        
        return true;
      } catch (error) {
        console.error('Connection error:', error);
        return false;
      }
    }
  
    async print(text) {
      if (!this.characteristic) {
        const connected = await this.connect();
        if (!connected) {
          return false;
        }
      }
  
      try {
        // Convert text to bytes
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        
        // Split data into chunks (Bluetooth has a limit on packet size)
        const chunkSize = 20;
        for (let i = 0; i < data.length; i += chunkSize) {
          const chunk = data.slice(i, i + chunkSize);
          await this.characteristic.writeValue(chunk);
        }
        
        // Add a form feed at the end
        await this.characteristic.writeValue(encoder.encode('\n\n\n\n\n'));
        
        return true;
      } catch (error) {
        console.error('Print error:', error);
        return false;
      }
    }
  
    disconnect() {
      if (this.device && this.device.gatt.connected) {
        this.device.gatt.disconnect();
      }
      this.device = null;
      this.characteristic = null;
    }
  }
  
  // Create a global instance
  window.bluetoothPrinter = new BluetoothPrinter();