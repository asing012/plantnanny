# 🌿 AI Plant Nanny

An autonomous plant monitoring system built with a **Raspberry Pi Pico W**. This "AI Nanny" tracks soil moisture, ambient light, and climate data, sending hourly status updates and health alerts directly to your phone via **ntfy.sh**.

## ✨ Features
* **Hourly Status Reports:** Sends a summary of plant health between 8 AM and 5 PM EST.
* **Smart Alerts:** Notifies you immediately if the soil is too dry or if the plant isn't getting enough light.
* **Data Logging:** Automatically saves sensor readings to `history.csv` for long-term health tracking.
* **Night Mode:** Respects your quiet hours by monitoring silently without sending notifications.

## 🛠️ Hardware Setup
* **Microcontroller:** Raspberry Pi Pico W.
* **Sensors:**
    * **Capacitive Soil Moisture Sensor:** Connected to ADC 26.
    * **BH1750 Light Sensor:** Connected via I2C (SCL Pin 1, SDA Pin 0).
    * **DHT11 Temperature & Humidity Sensor:** Connected to Pin 15.
* **Indicators:** Onboard LED flashes during alerts or to confirm a successful Wi-Fi connection.



## 🚀 Getting Started

### 1. Prerequisites
Ensure you have the MicroPython firmware installed on your Pico W and the **MicroPico** extension in VS Code.

### 2. Configuration
To keep your credentials safe, this project uses a `secrets.py` file which is excluded from Git via `.gitignore`.
1. Rename `secrets_template.py` to `secrets.py`.
2. Fill in your Wi-Fi SSID, Password, and your unique **ntfy** topic name.

```python
# secrets.py
SSID = "Your_WiFi_Name"
PASSWORD = "Your_WiFi_Password"
NTFY_TOPIC = "plant_nanny_aks"