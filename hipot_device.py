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
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False

    def connect(self) -> bool:
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
        if self.serial and self.serial.is_open:
            self.stop_test()
            self.serial.close()
        self.connected = False

    def send_command(self, command: str):
        if not self.connected or not self.serial:
            raise Exception("Urządzenie nie jest połączone!")
        if not command.endswith('\n'):
            command += '\n'
        self.serial.write(command.encode('ascii'))
        time.sleep(0.1)

    def read_response(self, timeout: float = 2.0) -> Optional[str]:
        if not self.connected or not self.serial:
            return None

        start_time = time.time()
        response = ""

        while (time.time() - start_time) < timeout:
            if self.serial.in_waiting > 0:
                chunk = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                response += chunk
                if '\n' in response or '\r' in response:
                    break
            time.sleep(0.05)

        return response.strip() if response else None

    def query(self, command: str) -> Optional[str]:
        self.send_command(command)
        return self.read_response()

    def configure_test(self, step: int, mode: str, params: Dict):
        if mode == 'AC':
            self.send_command(f"SAFE:STEP{step}:AC:LEV {params.get('voltage', 1000)}")
            self.send_command(f"SAFE:STEP{step}:AC:LIM:HIGH {params.get('current_limit_high', 0.005)}")
            self.send_command(f"SAFE:STEP{step}:AC:LIM:LOW {params.get('current_limit_low', 0.0)}")
            self.send_command(f"SAFE:STEP{step}:AC:TIME:TEST {params.get('duration', 60)}")
            self.send_command(f"SAFE:STEP{step}:AC:TIME:RAMP {params.get('ramp_time', 0)}")
            self.send_command(f"SAFE:STEP{step}:AC:TIME:FALL {params.get('fall_time', 0)}")
        elif mode == 'DC':
            self.send_command(f"SAFE:STEP{step}:DC:LEV {params.get('voltage', 1000)}")
            self.send_command(f"SAFE:STEP{step}:DC:LIM:HIGH {params.get('current_limit_high', 0.005)}")
            self.send_command(f"SAFE:STEP{step}:DC:LIM:LOW {params.get('current_limit_low', 0.0)}")
            self.send_command(f"SAFE:STEP{step}:DC:TIME:TEST {params.get('duration', 60)}")
            self.send_command(f"SAFE:STEP{step}:DC:TIME:RAMP {params.get('ramp_time', 0)}")
            self.send_command(f"SAFE:STEP{step}:DC:TIME:FALL {params.get('fall_time', 0)}")

    def start_test(self) -> bool:
        try:
            self.send_command("SAFE:STAR")
            return True
        except Exception as e:
            print(f"Błąd rozpoczęcia testu: {e}")
            return False

    def stop_test(self) -> bool:
        try:
            self.send_command("SAFE:STOP")
            return True
        except Exception as e:
            print(f"Błąd zatrzymania testu: {e}")
            return False

    def get_status(self) -> str:
        try:
            response = self.query("SAFE:STAT?")
            if response:
                return response.strip()
            return "UNKNOWN"
        except Exception as e:
            print(f"Błąd pobierania statusu: {e}")
            return "UNKNOWN"

    def read_measurements(self) -> Optional[Dict[str, float]]:
        try:
            response = self.query("SAFE:FETC? STEP,MODE,OMET,MMET,RMET")
            if response:
                parts = response.split(',')
                if len(parts) >= 5:
                    return {
                        'step':            int(parts[0]),
                        'mode':            parts[1].strip(),
                        'output_voltage':  float(parts[2]),  # V
                        'measure_current': float(parts[3]),  # A
                        'real_current':    float(parts[4])   # A
                    }
        except Exception as e:
            print(f"Błąd odczytu pomiarów: {e}")
        return None

    def get_test_result(self) -> Tuple[str, Dict]:
        try:
            judgment_code = self.query("SAFE:RES:LAST:JUDG?")
            output_v      = self.query("SAFE:RES:LAST:OMET?")
            measured_i    = self.query("SAFE:RES:LAST:MMET?")
            real_i        = self.query("SAFE:RES:LAST:RMET?")

            result = "PASS" if judgment_code and "116" in judgment_code else "FAIL"

            data = {
                'judgment_code':    judgment_code,
                'output_voltage':   float(output_v)   if output_v   else 0.0,
                'measured_current': float(measured_i) * 1000 if measured_i else 0.0,  # mA
                'real_current':     float(real_i)     * 1000 if real_i     else 0.0   # mA
            }
            return (result, data)

        except Exception as e:
            print(f"Błąd pobierania wyniku: {e}")
            return ("UNKNOWN", {})

    def clear_steps(self):
        try:
            num_steps = self.query("SAFE:SNUM?")
            if num_steps:
                n = int(float(num_steps))
                for i in range(n, 0, -1):
                    self.send_command(f"SAFE:STEP{i}:DEL")
        except Exception as e:
            print(f"Błąd czyszczenia kroków: {e}")