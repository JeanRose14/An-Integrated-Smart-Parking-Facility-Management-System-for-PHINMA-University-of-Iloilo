import serial
import requests
import time

SERIAL_PORT = "COM7"  # ⚠️ CHANGE if different
BAUD_RATE = 9600

def parse_line(line):
    try:
        if "AVAILABLE:" in line:
            parts = line.strip().split(",")
            available = int(parts[0].split(":")[1])
            total = int(parts[1].split(":")[1])

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