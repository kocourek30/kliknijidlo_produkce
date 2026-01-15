import serial
import requests
import time
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'RFID reader na COM3 pro vydej_jidel'

    def handle(self, *args, **options):
        API_URL = "http://localhost:8000/vydej_frontend/api/rfid-scan/"  # uprav URL
        ser = serial.Serial('COM3', 9600, timeout=1)
        self.stdout.write("RFID reader spuštěn na COM3...")
        
        while True:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    uid = line
                    self.stdout.write(f"RFID: {uid}")
                    requests.post(API_URL, json={'uid': uid}, timeout=3)
            except Exception as e:
                self.stdout.write(f"Chyba: {e}")
            time.sleep(0.1)
