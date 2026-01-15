# 🍽️ KlikniJídlo v2 - RFID Výdejní systém

Django aplikace pro správu výdeje jídel ve školní jídelně s podporou RFID čteček a real-time komunikací.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Django](https://img.shields.io/badge/Django-5.2-green)
![Node.js](https://img.shields.io/badge/Node.js-18+-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Hlavní funkce

- ✅ **RFID výdej** - Automatické načtení objednávky po přiložení karty
- ✅ **Real-time dashboard** - Socket.IO komunikace s RFID bridge serverem
- ✅ **Kiosk režim** - Automatické přihlášení pro výdejní terminály
- ✅ **Výdejní účtenky** - Automatické vytváření a tisk účtenek
- ✅ **Časové kontroly** - Respektování nastavených časů výdeje jídel
- ✅ **Responzivní UI** - Optimalizováno pro dotykové obrazovky
- ✅ **Částečný výdej** - Podpora výdeje různých jídel v různých časech
- ✅ **Debounce protection** - Ochrana proti duplicitním scanům

## 📋 Požadavky

- **Python** 3.13 nebo vyšší
- **Node.js** 18 nebo vyšší
- **SQLite** (nebo MySQL/PostgreSQL pro produkci)
- **RFID čtečka** (USB/Serial - např. RC522)
- **Windows** 10/11 (pro batch scripty) nebo Linux/Mac

## 🔧 Instalace

### 1. Klonování repozitáře

```bash
git clone https://github.com/kocourek30/kliknijidlo_v2_01.git
cd kliknijidlo_v2_01


2. Vytvoření virtuálního prostředí
bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
3. Instalace Python závislostí
bash
pip install -r requirements.txt
4. Instalace Node.js závislostí (pro RFID bridge)
bash
npm install
5. Migrace databáze
bash
python manage.py migrate
python manage.py createsuperuser
6. Vytvoření uživatele pro kiosk
bash
python manage.py setup_kiosk
Tento příkaz vytvoří uživatele vydej_terminal s heslem vydej2026.

7. Konfigurace RFID čtečky
Upravte COM port v souboru rfid_bridge.js:

javascript
const port = new SerialPort('COM3', { baudRate: 9600 });
// Změňte COM3 na váš port (např. COM4, /dev/ttyUSB0, atd.)
🖥️ Spuštění
Automaticky (Windows)
bash
start_vydej.bat
Tento skript:

✅ Aktivuje virtuální prostředí

✅ Spustí Django server (port 8000)

✅ Spustí RFID Bridge (port 3001)

✅ Otevře prohlížeč v kiosk režimu

✅ Automaticky přihlásí obsluhu

Manuálně
Terminal 1 - Django server:

bash
python manage.py runserver
Terminal 2 - RFID Bridge:

bash
node rfid_bridge.js
Terminal 3 - Prohlížeč:

bash
# Otevři URL:
http://127.0.0.1:8000/vydej/kiosk-login/
Zastavení systému
bash
stop_vydej.bat
📁 Struktura projektu
text
kliknijidlo_v2/
├── 📂 vydej_frontend/          # Výdejní dashboard s RFID
│   ├── views.py               # API endpointy pro výdej
│   ├── urls.py                # URL routy
│   └── templates/             # HTML šablony
├── 📂 objednavky/              # Správa objednávek
├── 📂 jidelnicek/              # Jídelníček a menu
├── 📂 users/                   # Uživatelé a RFID karty
├── 📂 dotace/                  # Dotační systém
├── 📂 canteen_settings/        # Nastavení jídelny
├── 📂 static/                  # CSS, JS, obrázky
│   └── js/
│       └── rfid_client.js     # Socket.IO klient (DEPRECATED)
├── 📂 templates/               # Globální šablony
├── 📄 rfid_bridge.js           # Node.js RFID server
├── 📄 start_vydej.bat          # Auto-start script
├── 📄 stop_vydej.bat           # Stop script
├── 📄 manage.py                # Django management
├── 📄 requirements.txt         # Python dependencies
└── 📄 package.json             # Node.js dependencies
🔌 RFID Bridge architektura
text
┌─────────────┐      USB/Serial      ┌──────────────┐
│ RFID čtečka │ ──────────────────> │ rfid_bridge  │
│  (RC522)    │                      │   (Node.js)  │
└─────────────┘                      └──────┬───────┘
                                            │
                                     Socket.IO
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │   Django     │
                                    │  (Frontend)  │
                                    └──────────────┘
Komunikační protokol:
Event: rfid_scanned

json
{
  "rfid": "2100B34B09"
}
Response:

✅ Načte objednávku uživatele

✅ Zobrazí položky k vydání

✅ Čeká na potvrzení obsluhou

🎨 UI Screenshots
Dashboard - Waiting state
text
┌──────────────────────────────────┐
│   🆔 RFID Čtečka připravena      │
│                                  │
│   Přiložte kartu k čtečce        │
│                                  │
│   🔌 Port: COM3 ✅               │
└──────────────────────────────────┘
Dashboard - Order loaded
text
┌──────────────────────────────────┐
│ 👤 Jan Novák                     │
│ 📅 Objednáno na: 11.01.2026      │
│                                  │
│ 🍽️ Položky k vydání:             │
│                                  │
│  2× Svíčková na smetaně          │
│  1× Čočková polévka              │
│  1× Čokoládový muffin            │
│                                  │
│ [✅ Vydat objednávku] [❌ Zrušit] │
└──────────────────────────────────┘
⚙️ Konfigurace
Django settings
Důležité nastavení v kliknijidlo/settings.py:

python
# Pro produkci změň:
DEBUG = False
SECRET_KEY = 'your-production-secret-key'
ALLOWED_HOSTS = ['your-domain.com', 'localhost']

# Databáze (pro produkci použij PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kliknijidlo',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
RFID Bridge konfigurace
V rfid_bridge.js:

javascript
// Port konfigurace
const PORT = 3001;  // Socket.IO server port
const SERIAL_PORT = 'COM3';  // RFID čtečka
const BAUD_RATE = 9600;  // Rychlost komunikace

// CORS nastavení
const io = require('socket.io')(PORT, {
    cors: {
        origin: "*",  // Pro produkci specifikuj doménu
        methods: ["GET", "POST"]
    }
});
🔒 Bezpečnost
Produkční checklist:
 Změň SECRET_KEY v Django settings

 Nastav DEBUG = False

 Nakonfiguruj ALLOWED_HOSTS

 Používej HTTPS

 Změň výchozí heslo pro vydej_terminal

 Omezte CORS v RFID bridge na konkrétní doménu

 Používej PostgreSQL místo SQLite

 Nastavte firewall pravidla

 Zálohujte databázi pravidelně

🧪 Testování
Test RFID bez čtečky:
Otevři konzoli prohlížeče (F12) a zadej:

javascript
testRFID('2100B34B09')
Test API endpoint:
bash
curl -X POST http://127.0.0.1:8000/vydej/rfid-scan/ \
  -H "Content-Type: application/json" \
  -d '{"rfid_tag": "2100B34B09"}'
📝 TODO / Budoucí vylepšení
 WebSocket místo polling pro rychlejší komunikaci

 Offline režim s lokální queue

 Tisk účtenek na síťové tiskárně

 Mobilní aplikace pro obsluhu

 Statistiky výdeje v reálném čase

 Integrace s platební bránou

 Multi-language support

 Dark mode

 PWA pro offline funkčnost

🐛 Řešení problémů
RFID čtečka nefunguje
bash
# Zkontroluj COM port
# Windows:
mode

# Linux:
ls /dev/tty*
Socket.IO se nepřipojí
bash
# Zkontroluj, zda běží bridge:
netstat -ano | findstr :3001

# Restartuj bridge:
node rfid_bridge.js
Django vyžaduje přihlášení
bash
# Použij kiosk login URL:
http://127.0.0.1:8000/vydej/kiosk-login/
📄 Licence
MIT License - viz LICENSE soubor

👨‍💻 Autor
Tomáš Kocourek

GitHub: @kocourek30

Email: tomas.kocourek@gthcatering.cz

🤝 Přispívání
Pull requesty jsou vítány! Pro větší změny prosím nejdřív otevřete issue.

Fork projekt

Vytvoř feature branch (git checkout -b feature/amazing-feature)

Commit změny (git commit -m 'Add amazing feature')

Push do branch (git push origin feature/amazing-feature)

Otevři Pull Request

📞 Podpora
Pokud narazíte na problém, otevřete Issue na GitHubu.

⭐ Pokud se vám projekt líbí, dejte mu hvězdičku! ⭐#   k l i k n i j i d l o _ p r o d u k c e  
 