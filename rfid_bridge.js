const { SerialPort } = require('serialport');
const express = require('express');
const cors = require('cors');
const { Server } = require('socket.io');
const http = require('http');
const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const fs = require('fs');
require('dotenv').config();

const app = express();
const server = http.createServer(app);

// Environment configuration
const BRIDGE_PORT = process.env.RFID_BRIDGE_PORT || 3001;
const ALLOWED_ORIGINS = process.env.RFID_ALLOWED_ORIGINS 
    ? process.env.RFID_ALLOWED_ORIGINS.split(',')
    : ['https://jidelna.kliknijidlo.cz', 'http://localhost:8000', 'http://127.0.0.1:8000'];

console.log('🔒 CORS povoleno pro:', ALLOWED_ORIGINS);

// CSV Logger configuration
const rfidCSVTransport = new DailyRotateFile({
    filename: 'logs/rfid_scans_%DATE%.csv',
    datePattern: 'YYYY-MM-DD',
    maxFiles: '14d',
    zippedArchive: true,
    format: winston.format.printf(({ timestamp, rfid_tag, user_name, action, order_id, ip }) => 
        `${timestamp},"${rfid_tag}","${user_name || ''}","${action}","${order_id || ''}","${ip || ''}"`
    )
});

const rfidLogger = winston.createLogger({
    transports: [
        rfidCSVTransport,
        new winston.transports.Console()
    ]
});

// CSV Header initialization
const logDir = './logs';
if (!fs.existsSync(logDir)) fs.mkdirSync(logDir);
const todayFile = `logs/rfid_scans_${new Date().toISOString().split('T')[0]}.csv`;
if (!fs.existsSync(todayFile)) {
    fs.writeFileSync(todayFile, 'timestamp,rfid_tag,user_name,action,order_id,ip\n');
}

// CORS configuration - secured for production
app.use(cors({
    origin: function(origin, callback) {
        // Allow requests with no origin (mobile apps, Postman, etc.)
        if (!origin) return callback(null, true);
        
        if (ALLOWED_ORIGINS.indexOf(origin) !== -1) {
            callback(null, true);
        } else {
            console.warn('⚠️  CORS blocked:', origin);
            callback(new Error('Not allowed by CORS'));
        }
    },
    methods: ["GET", "POST", "OPTIONS"],
    credentials: true,
    optionsSuccessStatus: 200
}));

app.use(express.json());

// Socket.IO with secured CORS
const io = new Server(server, {
    cors: {
        origin: ALLOWED_ORIGINS,
        methods: ["GET", "POST"],
        credentials: true
    },
    transports: ['websocket', 'polling'],
    pingTimeout: 20000,
    pingInterval: 25000
});

let serialPort = null;
let reconnectAttempts = 0;
const MAX_RECONNECTS = 10;
let buffer = '';
let lastScanTime = 0;
let processTimeout = null;
const EXPECTED_LENGTH = 16;

async function connectSerial() {
    if (serialPort) {
        try {
            await serialPort.close();
        } catch(e) {}
    }
    
    try {
        console.log(`🔄 Pokus ${reconnectAttempts + 1}/${MAX_RECONNECTS} o připojení COM3...`);
        serialPort = new SerialPort({ 
            path: 'COM3', 
            baudRate: 9600,
            autoOpen: false 
        });
        
        await serialPort.open();
        console.log('✅ RFID čtečka COM3 připojena!');
        reconnectAttempts = 0;
        
        serialPort.on('data', (data) => {
            const newData = data.toString('ascii');
            buffer += newData;
            lastScanTime = Date.now();
            
            console.log('📦 RAW BYTES:', data.length, 'bytes');
            console.log('📦 BUFFER:', JSON.stringify(buffer));
            
            if (processTimeout) {
                clearTimeout(processTimeout);
            }
            
            processTimeout = setTimeout(processBuffer, 300);
        });
        
        serialPort.on('error', (err) => {
            console.error('❌ Serial error:', err.message);
            reconnectAttempts++;
            if (reconnectAttempts < MAX_RECONNECTS) {
                setTimeout(connectSerial, 5000);
            }
        });
        
        serialPort.on('close', () => {
            console.log('🔌 COM3 odpojena');
            reconnectAttempts++;
            if (reconnectAttempts < MAX_RECONNECTS) {
                setTimeout(connectSerial, 3000);
            }
        });
        
    } catch (err) {
        console.error('❌ Chyba COM3:', err.message);
        reconnectAttempts++;
        if (reconnectAttempts < MAX_RECONNECTS) {
            setTimeout(connectSerial, 5000);
        }
    }
}

function processBuffer() {
    if (buffer.length === 0) {
        console.log('⚪ Prázdný buffer - ignorováno');
        return;
    }
    
    console.log('🔍 Zpracovávám buffer:', buffer.length, 'chars');
    
    const cleanBuffer = buffer.replace(/[\r\n\s]/g, '');
    const rfidMatch = cleanBuffer.match(/([0-9A-F]{16})/i);
    
    if (rfidMatch && rfidMatch[1].length === EXPECTED_LENGTH) {
        const rfid = rfidMatch[1].toUpperCase();
        
        console.log(`🆔 RFID KOMPLETNÍ: ${rfid} (${rfid.length} chars)`);
        console.log(`📡 Emitting to ${io.engine.clientsCount} clients`);
        
        io.emit('rfid_scanned', { 
            rfid_tag: rfid,
            raw_buffer: cleanBuffer,
            timestamp: new Date().toISOString()
        });
        
        // Log to CSV
        rfidLogger.info('SCAN_DETECTED', { 
            rfid_tag: rfid,
            raw_buffer: cleanBuffer,
            clients: io.engine.clientsCount
        });
    } else {
        console.log('❌ Neplatná RFID sekvence:', cleanBuffer.substring(0, 32) + '...');
    }
    
    buffer = '';
    processTimeout = null;
    console.log('🧹 Buffer reset - PŘIPRAVEN!');
}

// Health check endpoint
app.get('/status', (req, res) => {
    res.json({ 
        status: 'OK',
        port_open: serialPort?.isOpen || false,
        buffer_length: buffer.length,
        last_scan: Date.now() - lastScanTime,
        attempts: reconnectAttempts,
        clients: io.engine.clientsCount,
        expected_length: EXPECTED_LENGTH,
        allowed_origins: ALLOWED_ORIGINS
    });
});

// List available serial ports
app.get('/ports', async (req, res) => {
    const { SerialPort: SerialPortList } = require('serialport');
    const ports = await SerialPortList.list();
    res.json(ports.map(p => ({ path: p.path, manufacturer: p.manufacturer })));
});

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log('👤 Client připojen:', socket.id);
    
    // Log connection
    rfidLogger.info('CLIENT_CONNECT', { 
        socket_id: socket.id,
        ip: socket.handshake.address 
    });
    
    // Send status to new client
    socket.emit('status', { 
        port_open: serialPort?.isOpen || false,
        expected_length: EXPECTED_LENGTH 
    });
    
    socket.on('disconnect', () => {
        rfidLogger.info('CLIENT_DISCONNECT', { 
            socket_id: socket.id 
        });
        console.log('👤 Client odpojen:', socket.id);
    });
});

console.log('🌉 Starting RFID Bridge v2.5 - PRODUCTION SECURED');
connectSerial();

server.listen(BRIDGE_PORT, () => {
    console.log(`🚀 Bridge: http://localhost:${BRIDGE_PORT}`);
    console.log(`📊 Status: http://localhost:${BRIDGE_PORT}/status`);
    console.log(`🔒 CORS: ${ALLOWED_ORIGINS.join(', ')}`);
});
