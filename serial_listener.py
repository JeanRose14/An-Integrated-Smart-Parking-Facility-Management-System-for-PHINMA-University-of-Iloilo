import serial
import requests
import time

SERIAL_PORT = "COM7"
BAUD_RATE = 9600

last_available = None
last_total = None
last_rfid = None
last_sent_time = 0
MIN_INTERVAL = 1.5

def parse_line(line):
    global last_available, last_total, last_rfid, last_sent_time

    try:
        line = line.strip()
        if not line:
            return

        payload = {}

        if "RFID:" in line:
            parts = line.split(",")
            for p in parts:
                if "RFID:" in p:
                    payload["rfid"] = p.split(":")[1].strip()
                elif "AVAILABLE:" in p:
                    payload["available"] = int(p.split(":")[1])
                elif "TOTAL:" in p:
                    payload["total"] = int(p.split(":")[1])

        elif "AVAILABLE:" in line:
            parts = line.split(",")
            payload["available"] = int(parts[0].split(":")[1])
            payload["total"] = int(parts[1].split(":")[1])

        if not payload:
            return

        now = time.time()

        same_values = (
            payload.get("available") == last_available
            and payload.get("total") == last_total
            and payload.get("rfid") == last_rfid
        )
        if same_values:
            return

        if now - last_sent_time < MIN_INTERVAL:
            return

        requests.post(
            "http://127.0.0.1:5000/update-parking",
            json=payload,
            timeout=1
        )

        print("SENT TO FLASK:", payload)

        last_available = payload.get("available", last_available)
        last_total = payload.get("total", last_total)
        last_rfid = payload.get("rfid", last_rfid)
        last_sent_time = now

    except Exception as e:
        print("Parse error:", e)

def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Listening to Arduino...")

    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors="ignore")
            parse_line(line)

if __name__ == "__main__":
    main()
