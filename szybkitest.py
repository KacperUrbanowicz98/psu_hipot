import serial, time

s = serial.Serial("COM6", 9600, timeout=2)
time.sleep(0.5)

def q(cmd):
    s.write((cmd+"\n").encode())
    time.sleep(0.2)
    r = s.read(s.in_waiting).decode(errors="ignore").strip()
    print(f"  {cmd}  →  '{r}'")
    return r

q("SAFEty:RESult:LAST:JUDG?")
q("SAFEty:RESult:LAST:OMET?")
q("SAFEty:RESult:LAST:MMET?")
q("SAFEty:SNUMber?")
s.close()