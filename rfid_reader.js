// Potřebné balíčky npm i serialport ws
const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const WebSocket = require('ws');

const port = new SerialPort({
  path: 'COM3',
  baudRate: 9600,
});
const parser = port.pipe(new ReadlineParser({ delimiter: '\r' }));

// Spuštění WebSocket serveru na portu 8080 (můžete upravit)
const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', function connection(ws) {
  console.log('WebSocket klient připojen');
});

port.on('open', () => {
  console.log('Port otevřen, naslouchám RFID...');
});

parser.on('data', (data) => {
  const rfid = data.trim();
  console.log('Načtená RFID:', rfid);

  // Pošleme RFID všem připojeným websocket klientům (tedy prohlížečům)
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ type: 'rfid', rfid }));
    }
  });
});

port.on('error', (err) => {
  console.error('Chyba portu:', err.message);
});

port.on('close', () => {
  console.log('Port uzavřen');
});
