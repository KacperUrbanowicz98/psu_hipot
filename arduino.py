# arduino.py
"""
Narzędzie diagnostyczne: podsłuch ramek z Arduino (interlock).

Poprzednia wersja miała zaszyty port COM7 i 4800 baud, podczas gdy
aplikacja domyślnie używa ustawień z config.json (COM5 @ 9600) — testy
"nie działały", bo słuchały na innym porcie i innej prędkości.

Użycie:
    python arduino.py              # ustawienia z config.json
    python arduino.py COM7 9600    # ręcznie
"""
import sys
import time

import serial


def main():
    port, baud = None, None

    if len(sys.argv) >= 2:
        port = sys.argv[1]
    if len(sys.argv) >= 3:
        baud = int(sys.argv[2])

    if port is None or baud is None:
        try:
            from config import Config
            cfg = Config()
            port = port or cfg.INTERLOCK_PORT
            baud = baud or cfg.INTERLOCK_BAUDRATE
        except Exception as e:
            print(f"Nie udało się wczytać config.json ({e}) — używam COM5 @ 9600")
            port = port or "COM5"
            baud = baud or 9600

    print(f"Nasłuchuję na {port} @ {baud} baud (Ctrl+C aby przerwać)...\n")
    try:
        with serial.Serial(port, baud, timeout=3) as s:
            time.sleep(3)          # Leonardo resetuje się po otwarciu portu
            s.reset_input_buffer()
            empty = 0
            while True:
                line = s.readline().decode("ascii", errors="ignore").strip()
                if line:
                    empty = 0
                    print(f">>> {line}")
                else:
                    empty += 1
                    print(f"(brak danych... {empty})")
                    if empty >= 10:
                        print("\nBrak danych przez ~30 s — sprawdź szkic, "
                              "baudrate i kabel.")
                        break
    except KeyboardInterrupt:
        print("\nPrzerwano.")
    except Exception as e:
        print(f"BŁĄD: {e}")


if __name__ == "__main__":
    main()
