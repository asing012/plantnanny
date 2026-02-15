import network
import time
import dht
from machine import I2C, Pin, ADC
import secrets        # Your WiFi password file
import urequests      # Your notification library

# --- CONFIGURATION ---
NTFY_TOPIC = secrets.NTFY_TOPIC  # Your ntfy topic for notifications
UTC_OFFSET = -5       # NJ Time
START_HOUR = 8        # 8:00 AM
END_HOUR = 17         # 5:00 PM

# How long to sleep between checks? (3600 seconds = 1 Hour)
SLEEP_SECONDS = 3600 

# --- HARDWARE SETUP ---
led = Pin("LED", Pin.OUT)
moisture = ADC(26)
dht_sensor = dht.DHT11(Pin(15))
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)

# Light Sensor Init
devices = i2c.scan()
addr = 0x23 if 0x23 in devices else 0x5c if 0x5c in devices else None
if addr:
    try: i2c.writeto(addr, b"\x01"); time.sleep(0.1); i2c.writeto(addr, b"\x10")
    except: pass

# --- CONNECT WIFI ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(secrets.SSID, secrets.PASSWORD)
        print("Connecting to WiFi...", end="")
        while not wlan.isconnected():
            print(".", end="")
            time.sleep(1)
    print(f"\n✅ Online: {wlan.ifconfig()[0]}")
    # Blink LED to show we are awake
    for _ in range(3): led.toggle(); time.sleep(0.1)

# --- LOGGING FUNCTION ---
def log_data(timestamp, soil, lux, temp):
    filename = "history.csv"
    try:
        # Check if file exists, if not create header
        try:
            with open(filename, "r") as f: pass
        except OSError:
            with open(filename, "w") as f:
                f.write("Time,Soil,Light_Lux,Temp_C\n")
        
        # Append data
        with open(filename, "a") as f:
            line = f"{timestamp},{soil},{lux:.0f},{temp}\n"
            f.write(line)
            print(f"💾 Saved to log: {line.strip()}")
    except Exception as e:
        print(f"❌ Logging Error: {e}")

# --- NOTIFICATION FUNCTION ---
def send_alert(msg):
    print(f"📡 Sending: {msg}")
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        urequests.post(url, data=msg)
    except Exception as e:
        print(f"❌ Send Error: {e}")

# --- MAIN LOOP ---
# We use a loop that runs once, then sleeps for a long time
while True:
    connect_wifi() # Ensure we are connected
    
    # 1. Get Time
    try:
        t = time.gmtime()
        hour = (t[3] + UTC_OFFSET) % 24
        minute = t[4]
        timestamp = f"{t[0]}-{t[1]:02d}-{t[2]:02d} {hour}:{minute:02d}"
    except: 
        hour = 0; timestamp = "Unknown"

    # 2. Read Sensors
    soil_val = moisture.read_u16()
    
    lux = 0
    if addr:
        try:
            d = i2c.readfrom(addr, 2)
            lux = ((d[0] << 8) | d[1]) / 1.2
        except: pass

    temp = 0
    try: dht_sensor.measure(); temp = dht_sensor.temperature()
    except: pass

    # 3. Determine Status
    status = "HAPPY 🌿"
    if soil_val > 55000: status = "THIRSTY! 💧"
    elif lux < 1000 and (START_HOUR <= hour < END_HOUR): status = "LOW LIGHT ☁️"

    print(f"\n--- REPORT {timestamp} ---")
    print(f"Status: {status} | Soil: {soil_val} | Lux: {lux:.0f}")

    # 4. Save to File
    log_data(timestamp, soil_val, lux, temp)

    # 5. Send Notification (Only during active hours)
    if START_HOUR <= hour < END_HOUR:
        msg = f"Simba's Plant ({hour}:{minute:02d})\nStatus: {status}\nSoil: {soil_val}\nLight: {lux:.0f} Lux"
        send_alert(msg)
    else:
        print("zzz... Sleeping (Night Mode)")

    # 6. THE BIG SLEEP (1 Hour)
    print(f"Sleeping for {SLEEP_SECONDS} seconds...")
    time.sleep(SLEEP_SECONDS)