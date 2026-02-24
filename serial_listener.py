import serial
import requests
import time

SERIAL_PORT = "COM7"  # change if needed
BAUD_RATE = 9600

# ⭐ anti-spam memory
last_available = None
last_total = None
last_sent_time = 0
MIN_INTERVAL = 1.5  # seconds between sends

def parse_line(line):
    global last_available, last_total, last_sent_time

    try:
        if "AVAILABLE:" not in line:
            return

        parts = line.strip().split(",")
        available = int(parts[0].split(":")[1])
        total = int(parts[1].split(":")[1])

        now = time.time()

        # ✅ RULE 1 — ignore if same values
        if available == last_available and total == last_total:
            return

        # ✅ RULE 2 — cooldown protection
        if now - last_sent_time < MIN_INTERVAL:
            return

        payload = {
            "available": available,
            "total": total
        }

        requests.post(
            "http://127.0.0.1:5000/update-parking",
            json=payload,
            timeout=1
        )

        print("SENT TO FLASK:", payload)

        # ⭐ update memory
        last_available = available
        last_total = total
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