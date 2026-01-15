# KlikniJídlo v2 - Production Deployment Guide

## 📋 Pre-Deployment Checklist

### 1. Security Configuration

- [ ] **Generate new SECRET_KEY**
  ```bash
  python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
  ```

- [ ] **Create production .env file**
  ```bash
  cp .env.example .env
  nano .env  # Fill in all values
  ```

- [ ] **Verify .env is in .gitignore**
  ```bash
  grep -q "^.env$" .gitignore && echo "OK" || echo "ADD .env to .gitignore!"
  ```

- [ ] **Set DEBUG=False** in .env

- [ ] **Configure ALLOWED_HOSTS** with production domain:
  ```
  DJANGO_ALLOWED_HOSTS=jidelna.kliknijidlo.cz
  ```

- [ ] **Configure CSRF_TRUSTED_ORIGINS**:
  ```
  CSRF_TRUSTED_ORIGINS=https://jidelna.kliknijidlo.cz
  ```

### 2. Database Setup (PostgreSQL Recommended)

#### Install PostgreSQL
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib python3-dev libpq-dev
```

#### Create Database and User
```bash
sudo -u postgres psql
```

V PostgreSQL konzoli:
```sql
CREATE DATABASE kliknijidlo;
CREATE USER kliknijidlo_user WITH PASSWORD 'your-strong-password';
ALTER ROLE kliknijidlo_user SET client_encoding TO 'utf8';
ALTER ROLE kliknijidlo_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE kliknijidlo_user SET timezone TO 'Europe/Prague';
GRANT ALL PRIVILEGES ON DATABASE kliknijidlo TO kliknijidlo_user;
\q
```

#### Configure .env for PostgreSQL
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=kliknijidlo
DB_USER=kliknijidlo_user
DB_PASSWORD=your-strong-password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Application Setup

#### Clone Repository (if not already done)
```bash
cd /var/www  # or your preferred location
git clone https://github.com/kocourek30/kliknijidlo_v2_01.git
cd kliknijidlo_v2_01
git checkout v2_produkce
```

#### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Create Required Directories
```bash
mkdir -p logs media staticfiles
chmod 755 logs media staticfiles
```

#### Configure .env File
```bash
cp .env.example .env
nano .env
# Fill in all production values!
```

### 4. Django Setup

#### Run Migrations
```bash
python manage.py migrate
```

#### Create Superuser
```bash
python manage.py createsuperuser
```

#### Create Kiosk User
```bash
python manage.py createsuperuser --username vydej_terminal
# Use password from .env KIOSK_PASSWORD
```

#### Collect Static Files
```bash
python manage.py collectstatic --noinput
```

#### Test Configuration
```bash
python manage.py check --deploy
```

Tento příkaz zkontroluje bezpečnostní nastavení a upozorní na problémy.

### 5. SSL/HTTPS Configuration

#### Install Certbot (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
```

#### Obtain SSL Certificate
```bash
sudo certbot --nginx -d jidelna.kliknijidlo.cz
```

Následuj instrukce certbotu pro dokončení.

#### Automatic Renewal Test
```bash
sudo certbot renew --dry-run
```

### 6. Web Server Configuration

Máš připravené konfigurace pro Nginx/Apache - ujisti se, že obsahují:

- **SSL/HTTPS** redirect
- **Static files** serving z `/staticfiles/`
- **Media files** serving z `/media/`
- **Proxy pass** na Gunicorn/uWSGI
- **Security headers** (HSTS, X-Frame-Options, atd.)

### 7. RFID Bridge Setup

Pokud používáš RFID čtečky:

```bash
cd rfid-bridge  # nebo kde máš RFID bridge
npm install
```

Ujisti se, že `RFID_BRIDGE_PORT` a `RFID_ALLOWED_ORIGINS` jsou správně nastavené v .env.

### 8. Email Configuration (Optional ale doporučené)

Pro admin notifikace nastavit v .env:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
ADMIN_EMAIL=admin@kliknijidlo.cz
```

---

## 🚀 Deployment Steps

### 1. Start Application Service

Pokud používáš systemd service (měl bys mít připravený):

```bash
sudo systemctl start kliknijidlo
sudo systemctl enable kliknijidlo
sudo systemctl status kliknijidlo
```

### 2. Start RFID Bridge (pokud používáš)

```bash
sudo systemctl start rfid-bridge
sudo systemctl enable rfid-bridge
sudo systemctl status rfid-bridge
```

### 3. Restart Nginx

```bash
sudo systemctl restart nginx
sudo systemctl status nginx
```

### 4. Verify Logs

```bash
# Django logs
tail -f logs/django.log

# Security logs
tail -f logs/security.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Systemd service logs
sudo journalctl -u kliknijidlo -f
```

---

## ✅ Post-Deployment Verification

### 1. Security Headers Check

Navštiv: https://securityheaders.com/?q=jidelna.kliknijidlo.cz&followRedirects=on

Očekávaný výsledek: A nebo A+ rating

### 2. SSL Test

Navštiv: https://www.ssllabs.com/ssltest/analyze.html?d=jidelna.kliknijidlo.cz

Očekávaný výsledek: A nebo A+ rating

### 3. Functional Tests

- [ ] Přihlášení funguje
- [ ] Admin panel je dostupný (na změněné URL!)
- [ ] Static files se načítají (CSS, JS, obrázky)
- [ ] Registrace nových uživatelů
- [ ] Vytvoření objednávky
- [ ] RFID čtečka funguje (pokud používáš)
- [ ] Kiosk terminál funguje
- [ ] PDF reporty se generují
- [ ] Email notifikace fungují (test)

### 4. Performance Check

```bash
# Test response time
curl -w "@curl-format.txt" -o /dev/null -s https://jidelna.kliknijidlo.cz/

# Check database connections
python manage.py dbshell
\conninfo
```

### 5. Error Handling Test

Navštiv neexistující URL a ověř, že:
- 404 stránka se zobrazuje (ne debug page!)
- Error je zalogován v `logs/django.log`
- Debug info není viditelná

---

## 🔐 Security Hardening (Doporučené)

### 1. Change Admin URL

V `kliknijidlo/urls.py` změň:

```python
# PŘED:
path('admin/', admin.site.urls),

# PO (použij vlastní náhodný string):
path('secure-admin-kj2026/', admin.site.urls),
```

### 2. Install Fail2Ban

Ochrana proti brute-force útokům:

```bash
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
# Configure nginx-limit-req jail
sudo systemctl restart fail2ban
```

### 3. Install Django-Axes (Optional)

Rate limiting pro Django login:

```bash
pip install django-axes
```

Přidej do `INSTALLED_APPS` a nakonfiguruj.

### 4. Regular Security Updates

```bash
# Check for outdated packages
pip list --outdated

# Update Django security patches
pip install -U Django

# Update all packages (opatrně!)
pip install -U -r requirements.txt
```

---

## 💾 Backup Strategy

### 1. Database Backup Script

Vytvoř `/usr/local/bin/backup-kliknijidlo-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/kliknijidlo"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="kliknijidlo"
DB_USER="kliknijidlo_user"

mkdir -p $BACKUP_DIR

# PostgreSQL backup
export PGPASSWORD="your-db-password"
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

```bash
chmod +x /usr/local/bin/backup-kliknijidlo-db.sh
```

### 2. Setup Cron Job

```bash
sudo crontab -e
```

Přidej:
```
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-kliknijidlo-db.sh >> /var/log/kliknijidlo-backup.log 2>&1
```

### 3. Media Files Backup

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/kliknijidlo"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/var/www/kliknijidlo_v2_01"

tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C $APP_DIR media/

# Keep last 14 days
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +14 -delete
```

---

## 🐛 Troubleshooting

### Static Files Not Loading

```bash
python manage.py collectstatic --clear
python manage.py collectstatic --noinput
sudo systemctl restart kliknijidlo
```

### Database Connection Errors

```bash
# Test PostgreSQL connection
psql -U kliknijidlo_user -d kliknijidlo -h localhost

# Check PostgreSQL is running
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 500 Internal Server Error

```bash
# Check application logs
tail -f logs/django.log

# Check systemd service logs
sudo journalctl -u kliknijidlo -n 100

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### RFID Bridge Not Connecting

```bash
# Check service status
sudo systemctl status rfid-bridge

# Check WebSocket connection
wscat -c ws://localhost:3001

# Check serial port permissions
ls -l /dev/ttyUSB0  # nebo jiný port
sudo usermod -a -G dialout $(whoami)
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/kliknijidlo_v2_01

# Fix permissions
sudo chmod -R 755 /var/www/kliknijidlo_v2_01
sudo chmod -R 775 logs/ media/ staticfiles/
```

---

## 📊 Monitoring & Maintenance

### Daily Tasks
- [ ] Check error logs: `tail logs/django.log`
- [ ] Check security logs: `tail logs/security.log`
- [ ] Verify backups completed

### Weekly Tasks
- [ ] Review failed login attempts
- [ ] Check disk space: `df -h`
- [ ] Check database size: `du -sh media/ staticfiles/`

### Monthly Tasks
- [ ] Update security patches: `pip list --outdated`
- [ ] Review user accounts
- [ ] Test backup restoration
- [ ] SSL certificate renewal check: `sudo certbot certificates`

---

## 📞 Support & Resources

- **Django Security**: https://docs.djangoproject.com/en/5.2/topics/security/
- **Django Deployment Checklist**: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- **Let's Encrypt**: https://letsencrypt.org/
- **Security Headers**: https://securityheaders.com/
- **SSL Test**: https://www.ssllabs.com/ssltest/

---

## 🎉 Production Ready!

Pokud jsi prošel všemi kroky, tvoje aplikace je připravená pro produkční provoz na doméně **jidelna.kliknijidlo.cz**!

Hodně štěstí! 🚀
