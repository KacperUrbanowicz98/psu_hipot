# hipot_device.py
"""
Moduł komunikacji z urządzeniem Hi-Pot Chroma
"""
import serial
import time
from typing import Optional, Tuple, Dict


class ChromaHiPotDevice:
    """Klasa obsługująca komunikację z testerem Hi-Pot Chroma przez RS232"""

    def __init__(self, port: str = "COM1", baudrate: int = 9600):
        """
        Inicjalizacja urządzenia Hi-Pot Chroma

        Args:
            port: Port szeregowy (np. COM1)
            baudrate: Prędkość transmisji (domyślnie 9600)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False

    def connect(self) -> bool:
        """
        Nawiązuje połączenie z urządzeniem

        Returns:
            True jeśli połączono pomyślnie
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            time.sleep(0.5)
            self.connected = True

            # Test połączenia
            self.send_command("*IDN?")
            response = self.read_response()
            if response:
                print(f"Połączono z: {response}")
                return True
            return False

        except Exception as e:
            print(f"Błąd połączenia: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Rozłącza połączenie z urządzeniem"""
        if self.serial and self.serial.is_open:
            self.stop_test()  # Zatrzymaj test przed rozłączeniem
            self.serial.close()
        self.connected = False

    def send_command(self, command: str):
        """
        Wysyła komendę do urządzenia

        Args:
            command: Komenda SCPI
        """
        if not self.connected or not self.serial:
            raise Exception("Urządzenie nie jest połączone!")

        # Dodaj końcówkę linii (LF lub CR+LF)
        if not command.endswith('\n'):
            command += '\n'

        self.serial.write(command.encode('ascii'))
        time.sleep(0.1)  # Krótka pauza po wysłaniu

    def read_response(self, timeout: float = 2.0) -> Optional[str]:
        """
        Odczytuje odpowiedź z urządzenia

        Args:
            timeout: Maksymalny czas oczekiwania w sekundach

        Returns:
            Odpowiedź jako string lub None
        """
        if not self.connected or not self.serial:
            return None

        start_time = time.time()
        response = ""

        while (time.time() - start_time) < timeout:
            if self.serial.in_waiting > 0:
                chunk = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                response += chunk

                # Sprawdź czy mamy kompletną odpowiedź (kończy się \n)
                if '\n' in response or '\r' in response:
                    break
            time.sleep(0.05)

        return response.strip() if response else None

    def query(self, command: str) -> Optional[str]:
        """
        Wysyła komendę i czeka na odpowiedź

        Args:
            command: Komenda SCPI

        Returns:
            Odpowiedź z urządzenia
        """
        self.send_command(command)
        return self.read_response()

    def configure_test(self, step: int, mode: str, params: Dict):
        """
        Konfiguruje parametry testu dla danego kroku

        Args:
            step: Numer kroku (1-99)
            mode: Tryb testu ('AC', 'DC', 'IR')
            params: Słownik z parametrami testu
        """
        if mode == 'AC':
            # Ustawienia testu AC
            self.send_command(f"SAFE:STEP{step}:AC:LEV {params.get('voltage', 1000)}")
            self.send_command(f"SAFE:STEP{step}:AC:LIM:HIGH {params.get('current_limit', 0.005)}")
            self.send_command(f"SAFE:STEP{step}:AC:TIME:TEST {params.get('duration', 60)}")
            self.send_command(f"SAFE:STEP{step}:AC:TIME:RAMP {params.get('ramp_time', 2)}")

        elif mode == 'DC':
            # Ustawienia testu DC
            self.send_command(f"SAFE:STEP{step}:DC:LEV {params.get('voltage', 1000)}")
            self.send_command(f"SAFE:STEP{step}:DC:LIM:HIGH {params.get('current_limit', 0.005)}")
            self.send_command(f"SAFE:STEP{step}:DC:TIME:TEST {params.get('duration', 60)}")
            self.send_command(f"SAFE:STEP{step}:DC:TIME:RAMP {params.get('ramp_time', 2)}")

    def start_test(self) -> bool:
        """
        Rozpoczyna test Hi-Pot

        Returns:
            True jeśli test rozpoczęty pomyślnie
        """
        try:
            self.send_command("SAFE:STAR")
            return True
        except Exception as e:
            print(f"Błąd rozpoczęcia testu: {e}")
            return False

    def stop_test(self) -> bool:
        """
        Zatrzymuje test Hi-Pot

        Returns:
            True jeśli test zatrzymany pomyślnie
        """
        try:
            self.send_command("SAFE:STOP")
            return True
        except Exception as e:
            print(f"Błąd zatrzymania testu: {e}")
            return False

    def get_status(self) -> str:
        """
        Pobiera status urządzenia

        Returns:
            Status: 'RUNNING', 'STOPPED', lub 'UNKNOWN'
        """
        try:
            response = self.query("SAFE:STAT?")
            if response:
                return response.strip()
            return "UNKNOWN"
        except Exception as e:
            print(f"Błąd pobierania statusu: {e}")
            return "UNKNOWN"

    def read_measurements(self) -> Optional[Dict[str, float]]:
        """
        Odczytuje aktualne pomiary

        Returns:
            Słownik z pomiarami: {'step', 'mode', 'output_voltage', 'measure_current', 'real_current'}
        """
        try:
            # Zapytanie o dane: STEP, MODE, Output Meter, Measure Meter, Real Meter
            response = self.query("SAFE:FETC? STEP,MODE,OMET,MMET,RMET")

            if response:
                # Parsowanie odpowiedzi: "1,AC,5.000000E+02,7.000000E-05,7.000000E-05"
                parts = response.split(',')

                if len(parts) >= 5:
                    return {
                        'step': int(parts[0]),
                        'mode': parts[1].strip(),
                        'output_voltage': float(parts[2]),  # w V
                        'measure_current': float(parts[3]),  # w A (należy *1000 dla mA)
                        'real_current': float(parts[4])  # w A
                    }
        except Exception as e:
            print(f"Błąd odczytu pomiarów: {e}")

        return None

    def get_test_result(self) -> Tuple[str, Dict]:
        """
        Pobiera wynik testu

        Returns:
            Tuple (wynik, dane):
                wynik: 'PASS', 'FAIL', 'UNKNOWN'
                dane: słownik z szczegółami
        """
        try:
            # Kod wyniku testu (116 = PASS)
            judgment_code = self.query("SAFE:RES:LAST:JUDG?")
            output_v = self.query("SAFE:RES:LAST:OMET?")
            measured_i = self.query("SAFE:RES:LAST:MMET?")
            real_i = self.query("SAFE:RES:LAST:RMET?")

            # Dekodowanie wyniku (116 = PASS, inne kody = FAIL)
            result = "PASS" if judgment_code and "116" in judgment_code else "FAIL"

            data = {
                'judgment_code': judgment_code,
                'output_voltage': float(output_v) if output_v else 0,
                'measured_current': float(measured_i) * 1000 if measured_i else 0,  # Convert to mA
                'real_current': float(real_i) * 1000 if real_i else 0
            }

            return (result, data)

        except Exception as e:
            print(f"Błąd pobierania wyniku: {e}")
            return ("UNKNOWN", {})

    def clear_steps(self):
        """Czyści wszystkie ustawione kroki testowe"""
        try:
            # Sprawdź ile kroków jest ustawionych
            num_steps = self.query("SAFE:SNUM?")
            if num_steps:
                n = int(float(num_steps))
                for i in range(n, 0, -1):
                    self.send_command(f"SAFE:STEP{i}:DEL")
        except Exception as e:
            print(f"Błąd czyszczenia kroków: {e}")


class ChromaHiPotDeviceSimulator(ChromaHiPotDevice):
    """Symulator urządzenia Hi-Pot do testów bez sprzętu"""

    def __init__(self, port="DEMO", baudrate=9600):
        """Inicjalizacja symulatora"""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.test_active = False
        self.test_start_time = None
        self.configured_params = {}

    def connect(self):
        """Symuluje połączenie"""
        print("🔧 [SYMULATOR] Nawiązywanie połączenia...")
        time.sleep(0.5)
        self.connected = True
        print("✓ [SYMULATOR] Połączono!")
        return True

    def disconnect(self):
        """Symuluje rozłączenie"""
        print("🔧 [SYMULATOR] Rozłączanie...")
        self.connected = False
        self.test_active = False

    def send_command(self, command):
        """Symuluje wysyłanie komendy"""
        print(f"📤 [SYMULATOR] Wysłano: {command.strip()}")
        time.sleep(0.05)

    def read_response(self, timeout=2.0):
        """Symuluje odpowiedź"""
        return "OK"

    def query(self, command):
        """Symuluje zapytanie"""
        print(f"📤 [SYMULATOR] Zapytanie: {command.strip()}")

        if "*IDN?" in command:
            return "CHROMA,19054,SIMULATOR,V1.0"
        elif "STAT?" in command:
            return "RUNNING" if self.test_active else "STOPPED"

        return "OK"

    def configure_test(self, step, mode, params):
        """Symuluje konfigurację testu"""
        print(f"⚙️ [SYMULATOR] Konfiguracja STEP {step}:")
        print(f"   Tryb: {mode}")
        print(f"   Napięcie: {params.get('voltage')}V")
        print(f"   Limit prądu: {params.get('current_limit')}A")
        print(f"   Czas: {params.get('duration')}s")
        self.configured_params = params

    def start_test(self):
        """Symuluje start testu"""
        print("▶️ [SYMULATOR] START TESTU")
        self.test_active = True
        self.test_start_time = time.time()
        return True

    def stop_test(self):
        """Symuluje stop testu"""
        print("⏹️ [SYMULATOR] STOP TESTU")
        self.test_active = False
        return True

    def get_status(self):
        """Symuluje pobieranie statusu"""
        # Automatycznie zatrzymaj po czasie testu
        if self.test_active and self.test_start_time:
            total_time = self.configured_params.get('duration', 3) + \
                         self.configured_params.get('ramp_time', 0.5) + 0.5

            if time.time() - self.test_start_time > total_time:
                self.test_active = False
                return "STOPPED"

        return "RUNNING" if self.test_active else "STOPPED"

    def read_measurements(self):
        """Symuluje odczyt pomiarów"""
        if not self.test_active or not self.test_start_time:
            return {
                'step': 1,
                'mode': 'AC',
                'output_voltage': 0,
                'measure_current': 0,
                'real_current': 0
            }

        # Symuluj narastanie napięcia i prądu
        elapsed = time.time() - self.test_start_time
        ramp_time = self.configured_params.get('ramp_time', 0.5)
        test_time = self.configured_params.get('duration', 3)
        target_voltage = self.configured_params.get('voltage', 3000)
        target_current = self.configured_params.get('current_limit', 0.0025) * 0.3  # 30% limitu

        # Faza narastania
        if elapsed < ramp_time:
            voltage = target_voltage * (elapsed / ramp_time)
            current = target_current * (elapsed / ramp_time)
        # Faza testu
        elif elapsed < ramp_time + test_time:
            voltage = target_voltage
            # Dodaj małą losowość do prądu
            import random
            current = target_current * (0.9 + random.random() * 0.2)
        # Faza opadania
        else:
            fall_progress = elapsed - (ramp_time + test_time)
            voltage = target_voltage * max(0, 1 - fall_progress / 0.5)
            current = target_current * max(0, 1 - fall_progress / 0.5)

        return {
            'step': 1,
            'mode': 'AC',
            'output_voltage': voltage,
            'measure_current': current,
            'real_current': current
        }

    def get_test_result(self):
        """Symuluje wynik testu"""
        import random

        # 90% szans na PASS
        if random.random() < 0.9:
            result = "PASS"
            judgment_code = "116"
        else:
            result = "FAIL"
            judgment_code = "17"  # HI

        data = {
            'judgment_code': judgment_code,
            'output_voltage': self.configured_params.get('voltage', 3000),
            'measured_current': self.configured_params.get('current_limit', 0.0025) * 300,  # mA
            'real_current': self.configured_params.get('current_limit', 0.0025) * 300
        }

        print(f"📊 [SYMULATOR] Wynik testu: {result}")
        print(f"   Kod: {judgment_code}")
        print(f"   Napięcie: {data['output_voltage']}V")
        print(f"   Prąd: {data['measured_current']:.2f}mA")

        return (result, data)

    def clear_steps(self):
        """Symuluje czyszczenie kroków"""
        print("🗑️ [SYMULATOR] Czyszczenie kroków testowych")
