const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const WebSocket = require('ws');

const port = new SerialPort({
  path: 'COM3',
  baudRate: 9600,
});

const parser = port.pipe(new ReadlineParser({ delimiter: '\r' }));
const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', ws => console.log('✅ WebSocket připojen'));

port.on('open', () => console.log('✅ COM3 OK'));
parser.on('data', data => {
  const rfid = data.trim();
  console.log('📱 RFID:', rfid);
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ type: 'rfid', rfid }));
    }
  });
});

port.on('error', err => console.error('❌ PORT:', err.message));
console.log('🚀 Server na ws://localhost:8080');
