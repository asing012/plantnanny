from machine import ADC
from time import sleep

moisture = ADC(26)

print("Reading sensor")
while True:
    raw = moisture.read_u16()
    print("Reading - ", raw)
    sleep(1)