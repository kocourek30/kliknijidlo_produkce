# 🚀 Deployment Guide - Production na NAS

Návod pro nasazení aplikace KlikniJídlo v2 na NAS server s doménou **jidelna.kliknijidlo.cz**

---

## 📋 Pre-deployment Checklist

Před nasazením zkontroluj:

- [ ] NAS má Python 3.13+ a Node.js 18+
- [ ] NAS má přístup k internetu pro instalaci balíčků
- [ ] Máš SSH přístup k NAS
- [ ] Doména jidelna.kliknijidlo.cz je namířená na NAS IP
- [ ] SSL certifikát je připravený (Let's Encrypt doporučeno)
- [ ] RFID čtečka je připojená přes USB/Serial
- [ ] Máš admin přístup k webovému serveru (Nginx/Apache)

---

## 🔐 Krok 1: Bezpečnostní konfigurace

### 1.1 Vytvoř produkční .env soubor

```bash
cd /path/to/kliknijidlo_v2_01
cp .env.example .env
nano .env
```

### 1.2 Vygeneruj nový SECRET_KEY

```bash
# V Django shell:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Výstup zkopíruj do `.env` jako `DJANGO_SECRET_KEY=`

### 1.3 Vyplň .env soubor

```env
# Django Configuration
DJANGO_SECRET_KEY=tvuj-vygenerovany-secret-key-zde-12345
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=jidelna.kliknijidlo.cz,localhost,127.0.0.1

# Database (SQLite pro začátek, později PostgreSQL)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# RFID Bridge
RFID_BRIDGE_PORT=3001
RFID_ALLOWED_ORIGINS=https://jidelna.kliknijidlo.cz,http://localhost:8000

# Security
CSRF_TRUSTED_ORIGINS=https://jidelna.kliknijidlo.cz
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Kiosk Credentials (ZMĚŇ HESLO!)
KIOSK_USERNAME=vydej_terminal
KIOSK_PASSWORD=silne-heslo-pro-kiosk-2026

# Email (volitelné)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tvuj-email@gmail.com
EMAIL_HOST_PASSWORD=tvoje-app-password
ADMIN_EMAIL=admin@kliknijidlo.cz
```

### 1.4 Zabezpeč .env soubor

```bash
chmod 600 .env
chown www-data:www-data .env  # nebo tvůj webserver user
```

---

## 📦 Krok 2: Instalace závislostí

### 2.1 Python závislosti

```bash
# Vytvoř virtuální prostředí
python3 -m venv venv
source venv/bin/activate

# Nainstaluj balíčky
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.2 Node.js závislosti

```bash
npm install
```

---

## 🗄️ Krok 3: Databáze

### 3.1 Migrace

```bash
python manage.py migrate
```

### 3.2 Vytvoř superuživatele

```bash
python manage.py createsuperuser
# Email: admin@kliknijidlo.cz
# Password: (silné heslo)
```

### 3.3 Vytvoř kiosk uživatele

```bash
python manage.py setup_kiosk
# Nebo manuálně změň heslo v admin panelu
```

### 3.4 Collect static files

```bash
python manage.py collectstatic --noinput
```

---

## 🌐 Krok 4: Webserver konfigurace (Nginx)

### 4.1 Vytvoř Nginx config

```bash
sudo nano /etc/nginx/sites-available/kliknijidlo
```

### 4.2 Nginx konfigurace

```nginx
server {
    listen 80;
    server_name jidelna.kliknijidlo.cz;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name jidelna.kliknijidlo.cz;
    
    # SSL certifikáty
    ssl_certificate /etc/letsencrypt/live/jidelna.kliknijidlo.cz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jidelna.kliknijidlo.cz/privkey.pem;
    
    # SSL security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    client_max_body_size 20M;
    
    # Static files
    location /static/ {
        alias /path/to/kliknijidlo_v2_01/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /path/to/kliknijidlo_v2_01/media/;
    }
    
    # Django application (Gunicorn)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # RFID Bridge WebSocket proxy
    location /socket.io/ {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4.3 Aktivuj config

```bash
sudo ln -s /etc/nginx/sites-available/kliknijidlo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔧 Krok 5: Systemd služby

### 5.1 Gunicorn služba (Django)

```bash
sudo nano /etc/systemd/system/kliknijidlo.service
```

```ini
[Unit]
Description=KlikniJidlo Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/kliknijidlo_v2_01
Environment="PATH=/path/to/kliknijidlo_v2_01/venv/bin"
ExecStart=/path/to/kliknijidlo_v2_01/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /var/log/kliknijidlo/access.log \
    --error-logfile /var/log/kliknijidlo/error.log \
    kliknijidlo.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.2 RFID Bridge služba

```bash
sudo nano /etc/systemd/system/rfid-bridge.service
```

```ini
[Unit]
Description=KlikniJidlo RFID Bridge
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/kliknijidlo_v2_01
Environment="NODE_ENV=production"
ExecStart=/usr/bin/node /path/to/kliknijidlo_v2_01/rfid_bridge.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.3 Aktivuj služby

```bash
# Vytvoř log složku
sudo mkdir -p /var/log/kliknijidlo
sudo chown www-data:www-data /var/log/kliknijidlo

# Reload systemd
sudo systemctl daemon-reload

# Spusť služby
sudo systemctl start kliknijidlo
sudo systemctl start rfid-bridge

# Aktivuj autostart
sudo systemctl enable kliknijidlo
sudo systemctl enable rfid-bridge

# Zkontroluj status
sudo systemctl status kliknijidlo
sudo systemctl status rfid-bridge
```

---

## 🔒 Krok 6: SSL Certifikát (Let's Encrypt)

```bash
# Nainstaluj certbot
sudo apt install certbot python3-certbot-nginx

# Získej certifikát
sudo certbot --nginx -d jidelna.kliknijidlo.cz

# Test automatického obnovovania
sudo certbot renew --dry-run
```

---

## 🧪 Krok 7: Testování

### 7.1 Zkontroluj služby

```bash
# Django
curl -I https://jidelna.kliknijidlo.cz

# RFID Bridge
curl http://localhost:3001/status

# Nginx
sudo nginx -t

# Systemd služby
sudo systemctl status kliknijidlo rfid-bridge
```

### 7.2 Test RFID čtečky

```bash
# Zjisti COM port čtečky
ls /dev/ttyUSB* /dev/ttyACM*

# Uprav rfid_bridge.js pokud není COM3
nano rfid_bridge.js
# Změň: path: '/dev/ttyUSB0'  (nebo tvůj port)

# Restart bridge
sudo systemctl restart rfid-bridge
```

### 7.3 Přihlášení

1. Otevři: https://jidelna.kliknijidlo.cz/admin
2. Přihlaš se superuživatelem
3. Zkontroluj, že všechno funguje

---

## 📊 Krok 8: Monitoring a zálohy

### 8.1 Logy

```bash
# Django logy
tail -f /var/log/kliknijidlo/error.log

# RFID Bridge logy
sudo journalctl -u rfid-bridge -f

# Nginx logy
tail -f /var/log/nginx/error.log
```

### 8.2 Automatické zálohy databáze

```bash
# Vytvoř backup script
sudo nano /usr/local/bin/backup-kliknijidlo.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/path/to/kliknijidlo_v2_01/db.sqlite3"

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/db_backup_$DATE.sqlite3

# Ponechej pouze 7 posledních záloh
find $BACKUP_DIR -name "db_backup_*.sqlite3" -mtime +7 -delete
```

```bash
# Udělej executable
sudo chmod +x /usr/local/bin/backup-kliknijidlo.sh

# Přidej do crontab (každý den ve 2:00)
sudo crontab -e
# Přidej řádek:
0 2 * * * /usr/local/bin/backup-kliknijidlo.sh
```

---

## 🔄 Krok 9: Update workflow

### 9.1 Aktualizace kódu

```bash
cd /path/to/kliknijidlo_v2_01

# Pull nové změny
git pull origin v2_produkce

# Aktivuj venv
source venv/bin/activate

# Update závislosti
pip install -r requirements.txt
npm install

# Migrace
python manage.py migrate

# Collect static
python manage.py collectstatic --noinput

# Restart služby
sudo systemctl restart kliknijidlo rfid-bridge
```

---

## 🚨 Krok 10: Řešení problémů

### Služba se nespustí

```bash
# Zkontroluj logy
sudo journalctl -u kliknijidlo -n 50
sudo journalctl -u rfid-bridge -n 50

# Zkontroluj permissions
ls -la /path/to/kliknijidlo_v2_01
```

### RFID čtečka nefunguje

```bash
# Přidej www-data do dialout skupiny
sudo usermod -a -G dialout www-data

# Restart služby
sudo systemctl restart rfid-bridge
```

### 502 Bad Gateway

```bash
# Zkontroluj, že Gunicorn běží
sudo systemctl status kliknijidlo

# Zkontroluj port
sudo netstat -tlnp | grep 8000
```

---

## ✅ Post-deployment checklist

Po nasazení zkontroluj:

- [ ] Web běží na https://jidelna.kliknijidlo.cz
- [ ] Admin panel je přístupný
- [ ] RFID čtečka komunikuje
- [ ] Kiosk login funguje
- [ ] Výdejní dashboard funguje
- [ ] SSL certifikát je aktivní (zelený zámek)
- [ ] Automatické zálohy běží
- [ ] Logy se správně zapisují
- [ ] Email notifikace fungují (pokud nakonfigurováno)

---

## 📞 Podpora

Pokud narazíš na problém:

1. Zkontroluj logy (viz Krok 8.1)
2. Restart služeb: `sudo systemctl restart kliknijidlo rfid-bridge`
3. Otevři issue na GitHubu: https://github.com/kocourek30/kliknijidlo_v2_01/issues

---

**🎉 Gratulujeme! Aplikace je v produkci na jidelna.kliknijidlo.cz**
