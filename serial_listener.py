import serial
import requests

SERIAL_PORT = 'COM7'
BAUD_RATE = 9600
API_URL = 'http://127.0.0.1:5000/api/rfid'

ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

while True:
    uid = ser.readline().decode().strip()
    if uid:
        requests.post(API_URL, json={"uid": uid})