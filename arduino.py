import serial
import time

PORT = "COM7"

with serial.Serial(PORT, 4800, timeout=3) as s:
    time.sleep(3)          # Leonardo potrzebuje więcej czasu
    s.reset_input_buffer()
    print(f"Nasłuchuję na {PORT}...\n")
    for _ in range(50):    # czekaj na 50 linii lub Ctrl+C
        line = s.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f">>> {line}")
        else:
            print("(brak danych...)")