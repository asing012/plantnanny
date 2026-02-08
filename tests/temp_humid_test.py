import dht
from machine import Pin
from time import sleep

sensor = dht.DHT11(Pin(15))

print("Reading ")
while True:
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print("Temp ", temp, "C | Humidity", hum, "%")
    except Exception as e:
        print("DHT error:", e)
            
    sleep(2)