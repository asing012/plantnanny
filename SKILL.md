---
name: plant-nanny-daily
description: Daily plant monitoring — reads sensor data, assesses plant health from yesterday's photo, and sends a morning digest.
---

# Plant Nanny — daily task

## My setup
- Raspberry Pi Pico W monitors one plant, sends data every hour over WiFi
- All files are in the Plant AI folder on the desktop
- Sensor data is in plant_data_snapshot.json (preferred) or plant_nanny.db (fallback)
- Photos are in the photos\ subfolder of the Plant AI folder, taken daily at 6pm
- Notifications go to ntfy topic: plant_nanny_aks
- Timezone: NJ, UTC-5

## My plant
- Philodendron Brasil, on my desk next to an iMac with a grow light above it
- Soil moisture: 40-70% healthy. Water when consistently below 35% for 2+ readings
- Light: 1000-3000 lux indirect. Grow light compensates for low natural light
- Temperature: 18-28°C ideal
- Humidity: 35%+ preferred
- Currently showing some stress — brown tips and one large brown leaf. Monitor closely but don't over-alarm

## What normal looks like
- Soil drops 0.1-0.2% per hour normally. Faster than 0.8%/hr sustained = anomalous
- Light below 200 lux during 8am-6pm = sensor issue, not a plant problem
- Evening and night lux of 0-2 is normal — do not flag
- DHT11 reads artificially high (too close to plant) — treat as relative, not absolute
- Soil moisture sensor is near the surface — reads dry faster than root zone reality. Be conservative

## Sensor data notes
- ALWAYS use received_at for ordering and time queries — never timestamp (has a timezone bug pre April 24 2026)
- Pico is online if received_at shows recent entries — that is the only reliable indicator
- Query hints:
  - Last 24h: WHERE received_at > datetime('now', '-24 hours')
  - Last 7 days: WHERE received_at > datetime('now', '-7 days')
  - Always ORDER BY received_at ASC for trends

## Notification rules
- Minimal interruptions — only push if I genuinely need to do something TODAY
- No alerts for single anomalous readings — need 2-3 consecutive readings
- Never send the same alert twice within 48 hours
- Daily digest is 2-3 sentences max, plain prose, no bullet points
- If nothing needs action, say so clearly and briefly

## Watering snooze logic
- If "watered_confirmed" appears in ntfy history after the last alert → suppress soil_dry alerts for 48 hours
- If soil moisture increases more than 15% between two consecutive readings → infer watering, reset alert window
- Log all watering events (confirmed or inferred) to watering_log.txt with timestamp and method

## Anomaly detection
SENSOR anomaly (hardware glitch — notify immediately):
- Soil changes more than 20% in a single hour
- Soil reads exactly 0% or 100%
- Lux reads 0 during 8am-6pm
- Temperature below 0°C or above 50°C
- Two or more sensors null in the same reading

PLANT anomaly (real change — include in digest, push only if urgent):
- Soil drying more than 2x the 7-day average rate
- Lux drop >50% vs same time yesterday sustained 3+ hours during 8am-6pm
- Temperature outside 15-30°C for 2+ consecutive readings

Use sensor anomaly detection only for the first 14 days of data.
After 14 days enable plant anomaly detection using rolling 7-day baseline.
Always distinguish sensor vs plant anomalies — they need different responses.

---

## Run in this order

### 0. Load today's photo
- Find the most recent .jpg in the photos\ subfolder of the Plant AI folder
- Photos are taken at 6pm daily after the grow light is off
- If today's photo does not exist, use yesterday's and note this in the digest
- If the photo is washed out or overexposed, note it and use sensor data alone
- Keep the photo ready for step 5

### 1. Read sensor data
Read plant_data_snapshot.json in the Plant AI folder.
Parse the "readings" array (newest-first).
Calculate from the last 24 hours (filter by received_at):
average soil moisture, min soil moisture, average lux, average temp,
average humidity, average soil drop rate.
Also pull last 7 days of soil_drop_rate for baseline drying rate.

Check "generated_at" — if more than 2 hours old, note Pico or server may
be offline and proceed with most recent available data rather than failing.

If plant_data_snapshot.json is missing: fall back to plant_nanny.db but do
NOT open with sqlite3 (cross-OS locking makes it appear malformed). Instead
search the binary for '{"readings":' strings and parse the JSON payloads directly.

### 2. Check watering log
Read watering_log.txt if it exists. Note last watering timestamp and method
(confirmed or inferred).

### 3. Check ntfy history
Check ntfy topic plant_nanny_aks message history for any "watered_confirmed"
message in the last 48 hours.

### 4. Run anomaly detection
Apply anomaly detection rules above. Sensor-only if under 14 days of data,
full detection after that.

### 5. Assess and decide
Check daily_log.txt first to avoid re-alerting for anything already flagged today.

Be conservative — remember the soil sensor reads dry faster than root zone
reality, and the DHT11 humidity reads high due to placement.

Look at the photo from step 0 and assess:
- Leaf color — yellowing, browning, unusual discoloration?
- Drooping — wilting leaves or drooping stems?
- New growth — any new leaves emerging?
- Overall — stressed or healthy?

Combine photo with sensor data:
- Sensors fine but plant looks stressed → trust the photo
- Sensors say dry but plant looks perky → be conservative before alerting

### 6. Send morning digest
Send ONE ntfy message to plant_nanny_aks:
- Title: "🌿 Good morning — plant update"
- Body: 2-3 sentences plain prose. Overall health, any trend worth knowing,
  exactly what I need to do today if anything. Include one observation
  from the photo — e.g. "leaves looking perky" or "noticed some yellowing
  on lower leaves"
- If watering needed: add action button "✓ Watered" that posts
  "watered_confirmed" back to the topic
- Priority: min if nothing needed, default if action needed

### 7. Log the run
If anomaly detected, append to daily_log.txt.
Always append one line regardless:
date | avg_soil% | avg_lux | action_needed: yes/no | one sentence summary