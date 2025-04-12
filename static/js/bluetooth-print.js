// Fixed bluetooth-print.js
class BluetoothPrinter {
  constructor() {
    this.device = null;
    this.characteristic = null;
    this.server = null;
    this.service = null;
  }

  async connect(specificDevice = null) {
    try {
      console.log('Requesting Bluetooth device...');
      
      let requestOptions = {};
      
      // If we have a specific device name to target
      if (specificDevice) {
        console.log(`Targeting specific device: ${specificDevice}`);
        requestOptions = {
          // Target the specific device by name if provided
          filters: [
            { name: specificDevice }
          ],
          optionalServices: [
            0x180F, // Battery service
            '0000ff00-0000-1000-8000-00805f9b34fb',
            '49535343-fe7d-4ae5-8fa9-9fafd205e455',
            '000018f0-0000-1000-8000-00805f9b34fb',
            'e7810a71-73ae-499d-8c15-faa9aef0c3f2'
          ]
        };
      } else {
        // More flexible approach to filter all potential printer devices
        requestOptions = {
          filters: [
            // Common printer-related filters
            { namePrefix: 'Printer' },
            { namePrefix: 'POS' },
            { namePrefix: 'BT' },
            { namePrefix: 'TP' },
            { namePrefix: 'ZJ' },
            { namePrefix: 'TC' }
          ],
          optionalServices: [
            0x180F, // Battery service
            '0000ff00-0000-1000-8000-00805f9b34fb',
            '49535343-fe7d-4ae5-8fa9-9fafd205e455',
            '000018f0-0000-1000-8000-00805f9b34fb',
            'e7810a71-73ae-499d-8c15-faa9aef0c3f2'
          ]
        };
      }
      
      // Request the device
      this.device = await navigator.bluetooth.requestDevice(requestOptions);

      console.log('Device selected:', this.device.name);
      this.deviceName = this.device.name || 'Unknown Printer';
      
      // Connect to the device
      console.log('Connecting to GATT server...');
      this.server = await this.device.gatt.connect();
      
      // Try multiple service UUIDs that are common for printers
      const serviceUUIDs = [
        '0000ff00-0000-1000-8000-00805f9b34fb',
        '49535343-fe7d-4ae5-8fa9-9fafd205e455',
        '000018f0-0000-1000-8000-00805f9b34fb',
        'e7810a71-73ae-499d-8c15-faa9aef0c3f2'
      ];
      
      // Try each service UUID until one works
      for (const serviceUUID of serviceUUIDs) {
        try {
          console.log(`Trying to get service: ${serviceUUID}...`);
          this.service = await this.server.getPrimaryService(serviceUUID);
          console.log(`Service found: ${serviceUUID}`);
          break;
        } catch (error) {
          console.log(`Service ${serviceUUID} not found, trying next...`);
          continue;
        }
      }
      
      if (!this.service) {
        // If we couldn't find any of our predefined services, try to get all services
        console.log('Trying to discover all services...');
        const services = await this.server.getPrimaryServices();
        console.log(`Found ${services.length} services`);
        
        if (services.length > 0) {
          this.service = services[0]; // Use the first service
          console.log(`Using first available service: ${this.service.uuid}`);
        } else {
          throw new Error('No services found on the device');
        }
      }
      
      // Get all characteristics for the service
      console.log('Getting characteristics...');
      const characteristics = await this.service.getCharacteristics();
      console.log(`Found ${characteristics.length} characteristics`);
      
      // Find a characteristic that allows writing
      for (const characteristic of characteristics) {
        const properties = characteristic.properties;
        console.log(`Characteristic ${characteristic.uuid} properties:`, properties);
        
        if (properties.write || properties.writeWithoutResponse) {
          this.characteristic = characteristic;
          console.log(`Using characteristic: ${characteristic.uuid} for writing`);
          break;
        }
      }
      
      if (!this.characteristic) {
        throw new Error('No writable characteristic found');
      }
      
      return true;
    } catch (error) {
      console.error('Connection error:', error);
      throw error;
    }
  }

  async tryDirectWrite(text) {
    // This is a fallback method that tries a more direct approach
    // for printers that don't follow standard ESC/POS protocols
    try {
      console.log('Trying direct write method...');
      
      // Convert text to bytes
      const encoder = new TextEncoder();
      const data = encoder.encode(text);
      
      // Find all services
      const services = await this.server.getPrimaryServices();
      console.log(`Found ${services.length} services for direct write attempt`);
      
      for (const service of services) {
        try {
          console.log(`Trying service: ${service.uuid}`);
          const characteristics = await service.getCharacteristics();
          
          for (const characteristic of characteristics) {
            if (characteristic.properties.write || characteristic.properties.writeWithoutResponse) {
              console.log(`Found writable characteristic: ${characteristic.uuid}`);
              
              // Split data into chunks (Bluetooth has a limit on packet size)
              const chunkSize = 20;
              for (let i = 0; i < data.length; i += chunkSize) {
                const chunk = data.slice(i, i + chunkSize);
                await characteristic.writeValue(chunk);
                await new Promise(resolve => setTimeout(resolve, 50));
              }
              
              console.log('Direct write attempt completed');
              return true;
            }
          }
        } catch (error) {
          console.log(`Error with service ${service.uuid}:`, error);
          continue;
        }
      }
      
      throw new Error('No writable characteristic found in any service');
    } catch (error) {
      console.error('Direct write failed:', error);
      throw error;
    }
  }

  async print(text) {
    if (!this.device || !this.server) {
      throw new Error('Not connected to a printer. Please connect first.');
    }

    try {
      console.log('Printing text:', text);
      
      // If we have a characteristic, use it
      if (this.characteristic) {
        // Convert text to bytes
        const encoder = new TextEncoder();
        let data = encoder.encode(text);
        
        // Add ESC/POS commands for initialization and text mode
        const init = new Uint8Array([0x1B, 0x40]); // ESC @ - Initialize printer
        const textMode = new Uint8Array([0x1B, 0x21, 0x00]); // ESC ! 0 - Normal text mode
        const feedAndCut = new Uint8Array([0x0A, 0x0A, 0x0A, 0x0A]); // Line feeds
        
        // Combine commands and text
        const fullData = new Uint8Array(init.length + textMode.length + data.length + feedAndCut.length);
        fullData.set(init, 0);
        fullData.set(textMode, init.length);
        fullData.set(data, init.length + textMode.length);
        fullData.set(feedAndCut, init.length + textMode.length + data.length);
        
        // Split data into chunks (Bluetooth has a limit on packet size)
        const chunkSize = 20;
        console.log(`Sending ${fullData.length} bytes in chunks of ${chunkSize}...`);
        
        for (let i = 0; i < fullData.length; i += chunkSize) {
          const chunk = fullData.slice(i, i + chunkSize);
          await this.characteristic.writeValue(chunk);
          
          // Add a small delay between chunks to prevent buffer overflow
          await new Promise(resolve => setTimeout(resolve, 50));
        }
        
        console.log('Print job sent successfully');
        return true;
      } else {
        // Fallback to direct write method
        return await this.tryDirectWrite(text);
      }
    } catch (error) {
      console.error('Print error:', error);
      
      // Try the direct write method as a fallback
      try {
        console.log('Trying fallback print method...');
        return await this.tryDirectWrite(text);
      } catch (fallbackError) {
        console.error('Fallback print method also failed:', fallbackError);
        throw error; // Throw the original error
      }
    }
  }

  disconnect() {
    if (this.device && this.device.gatt.connected) {
      this.device.gatt.disconnect();
      console.log('Disconnected from device');
    }
    this.device = null;
    this.server = null;
    this.service = null;
    this.characteristic = null;
  }
}

// Create a global instance
window.bluetoothPrinter = new BluetoothPrinter();