import network, time, dht, ntptime, json
from machine import I2C, Pin, ADC
import secrets, urequests

# --- CONFIG ---
SERVER_URL          = secrets.SERVER_URL
UTC_OFFSET          = -5
START_HOUR          = 8
END_HOUR            = 22
SLEEP_SECONDS       = 3600
SOIL_DRY_THRESHOLD  = 55000
SOIL_WET_THRESHOLD  = 20000
LUX_LOW_THRESHOLD   = 1000
TEMP_HIGH_THRESHOLD = 30
HUMIDITY_LOW        = 40
MOISTURE_DROP_ALERT = 3000

# --- HARDWARE ---
led          = Pin("LED", Pin.OUT)
moisture_adc = ADC(26)
dht_sensor   = dht.DHT11(Pin(15))
i2c          = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)

devices     = i2c.scan()
bh1750_addr = 0x23 if 0x23 in devices else 0x5c if 0x5c in devices else None
if bh1750_addr:
    try:
        i2c.writeto(bh1750_addr, b"\x01"); time.sleep(0.1)
        i2c.writeto(bh1750_addr, b"\x10")
    except: pass

# --- STATE ---
last_soil_val = None
_wlan = network.WLAN(network.STA_IF)

# --- WIFI ---
def ensure_wifi():
    _wlan.active(True)
    if _wlan.isconnected():
        return True
    print("Connecting...", end="")
    _wlan.connect(secrets.SSID, secrets.PASSWORD)
    for _ in range(20):
        if _wlan.isconnected():
            print(f"\n✅ {_wlan.ifconfig()[0]}")
            return True
        print(".", end=""); time.sleep(1)
    print("\n❌ WiFi failed"); return False

# --- SENSORS ---
def read_soil():
    return sum(moisture_adc.read_u16() for _ in range(5)) // 5

def read_lux():
    if not bh1750_addr: return None
    try:
        d = i2c.readfrom(bh1750_addr, 2)
        return round(((d[0] << 8) | d[1]) / 1.2, 1)
    except: return None

def read_dht():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except: return None, None

def get_timestamp():
    t = time.gmtime()
    # Adjust for UTC offset properly including date rollover
    import time as utime
    local = utime.mktime(t) + (UTC_OFFSET * 3600)
    lt = utime.gmtime(local)
    if lt[0] < 2024:
        hour = (t[3] + UTC_OFFSET) % 24
        return f"nosync-{hour}:{t[4]:02d}", t, (t[3] + UTC_OFFSET) % 24, t[4]
    return f"{lt[0]}-{lt[1]:02d}-{lt[2]:02d}T{lt[3]:02d}:{lt[4]:02d}:00", t, lt[3], lt[4]

# --- ALERTS ---
def evaluate_alerts(soil, lux, temp, humidity, drop_rate, hour):
    alerts = []
    in_day = START_HOUR <= hour < END_HOUR

    if soil > SOIL_DRY_THRESHOLD:
        alerts.append({"trigger": "soil_dry",
                        "severity": "critical" if soil > 60000 else "warn",
                        "reason": f"Soil at {soil} (threshold {SOIL_DRY_THRESHOLD})"})
    elif soil < SOIL_WET_THRESHOLD:
        alerts.append({"trigger": "soil_overwatered", "severity": "warn",
                        "reason": f"Soil at {soil} — possibly overwatered"})

    if drop_rate is not None and drop_rate > MOISTURE_DROP_ALERT:
        alerts.append({"trigger": "soil_drying_fast", "severity": "info",
                        "reason": f"Dropping {drop_rate} ADC units since last cycle"})

    if lux is not None and lux < LUX_LOW_THRESHOLD and in_day:
        alerts.append({"trigger": "low_light", "severity": "info",
                        "reason": f"Only {lux} lux during daylight"})

    if temp is not None and temp > TEMP_HIGH_THRESHOLD:
        alerts.append({"trigger": "high_temp", "severity": "warn",
                        "reason": f"Temp is {temp}°C"})

    if humidity is not None and humidity < HUMIDITY_LOW:
        alerts.append({"trigger": "low_humidity", "severity": "info",
                        "reason": f"Humidity at {humidity}%"})
    return alerts

def build_event(ts, soil, lux, temp, humidity, drop_rate, alerts):
    return {
        "timestamp": ts,
        "plant": "philodendron_brasil",
        "readings": {
            "soil_raw":          soil,
            "soil_moisture_pct": round(100 - (soil / 65535 * 100), 1),
            "lux":               lux,
            "temp_c":            temp,
            "humidity_pct":      humidity,
            "soil_drop_rate":    drop_rate
        },
        "alerts": alerts,
        "status": "alert" if alerts else "ok",
        "outcome": None
    }

# --- SEND ---
def post_event(event):
    try:
        urequests.post(SERVER_URL, data=json.dumps(event),
                       headers={"Content-Type": "application/json"})
        print("📡 Posted to server")
    except Exception as e:
        print(f"❌ Server error: {e}")

def log_csv(ts, soil, lux, temp, humidity):
    try:
        try: open("history.csv","r").close()
        except OSError:
            with open("history.csv","w") as f:
                f.write("timestamp,soil_raw,lux,temp_c,humidity_pct\n")
        with open("history.csv","a") as f:
            f.write(f"{ts},{soil},{lux},{temp},{humidity}\n")
    except Exception as e:
        print(f"❌ CSV error: {e}")

# --- STARTUP ---
print("🌿 Plant Nanny starting...")
if ensure_wifi():
    time.sleep(5)  # give WiFi a moment to stabilise

    try: ntptime.settime(); print("✅ Time synced")
    except: print("❌ Time sync failed")
    post_event({"type": "startup", "timestamp": get_timestamp()[0], "status": "online"})
    for _ in range(3): led.toggle(); time.sleep(0.1)

# --- MAIN LOOP ---
while True:
    ensure_wifi()
    ts, t, hour, minute = get_timestamp()
    soil           = read_soil()
    lux            = read_lux()
    temp, humidity = read_dht()

    drop_rate     = (soil - last_soil_val) if last_soil_val is not None else None
    last_soil_val = soil

    print(f"\n--- {ts} | Soil:{soil} Lux:{lux} Temp:{temp} RH:{humidity} Drop:{drop_rate}")

    alerts = evaluate_alerts(soil, lux, temp, humidity, drop_rate, hour)
    event  = build_event(ts, soil, lux, temp, humidity, drop_rate, alerts)

    log_csv(ts, soil, lux, temp, humidity)
    post_event(event)

    print(f"Sleeping {SLEEP_SECONDS}s...")
    time.sleep(SLEEP_SECONDS)