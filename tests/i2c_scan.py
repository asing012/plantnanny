from machine import I2C, Pin

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=50000)  # slower = more reliable

devices = i2c.scan()
print("I2C devices:", [hex(d) for d in devices])
