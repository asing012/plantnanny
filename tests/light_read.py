from machine import I2C, Pin
from time import sleep

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=10000)

devices = i2c.scan()
addr = 0x23 if 0x23 in devices else 0x5c if 0x5c in devices else None
print("I2C:", [hex(d) for d in devices], "addr:", hex(addr) if addr else None)
if addr is None:
    raise RuntimeError("BH1750 not found")

def init():
    sleep(0.2)
    i2c.writeto(addr, b"\x01")  # power on
    sleep(0.1)
    i2c.writeto(addr, b"\x10")  # continuous high-res
    sleep(0.2)

init()

MEASURE_DELAY = 0.4

while True:
    try:
        sleep(MEASURE_DELAY)
        data = i2c.readfrom(addr, 2)
        raw = (data[0] << 8) | data[1]
        lux = raw / 1.2
        print("Lux:", lux)
    except OSError as e:
        print("BH1750 read error:", e, "— reinitializing...")
        init()
    sleep(0.5)
