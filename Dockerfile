# Dockerfile pro Django aplikaci kliknijidlo
FROM python:3.11-slim

# Nastavení pracovního adresáře
WORKDIR /app

# Proměnné prostředí
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=kliknijidlo.settings

# Instalace systémových závislostí
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    musl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopírování requirements a instalace Python balíčků
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování celého projektu
COPY . .

# Vytvoření adresářů pro statické soubory a logy
RUN mkdir -p staticfiles media logs

# Vystavení portu
EXPOSE 8000

# Spuštění Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "kliknijidlo.wsgi:application"]
