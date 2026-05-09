"""
plant_server.py — runs on your Windows machine
pip install flask
python plant_server.py
"""

import sqlite3, json, os, tempfile
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app          = Flask(__name__)
DB_PATH      = "plant_nanny.db"
SNAPSHOT_PATH = "plant_data_snapshot.json"
#del "C:\Users\anily_5vi1dym\Desktop\Plant AI\plant_nanny.db"
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at    TEXT NOT NULL,
                timestamp      TEXT,
                plant          TEXT,
                status         TEXT,
                soil_raw       INTEGER,
                soil_pct       REAL,
                lux            REAL,
                temp_c         REAL,
                humidity_pct   REAL,
                soil_drop_rate INTEGER,
                alerts_json    TEXT,
                raw_payload    TEXT
            );
        """)
    print(f"✅ DB ready at {DB_PATH}")

def write_snapshot():
    """Write plant_data_snapshot.json atomically from the last 200 DB readings."""
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT received_at, timestamp, soil_pct, lux, temp_c,
                       humidity_pct, soil_drop_rate, alerts_json
                FROM events
                WHERE timestamp NOT LIKE 'nosync%%'
                ORDER BY received_at DESC
                LIMIT 200
            """).fetchall()

        readings = []
        for row in rows:
            try:
                alerts = json.loads(row["alerts_json"]) if row["alerts_json"] else []
            except Exception:
                alerts = []
            readings.append({
                "received_at":    row["received_at"],
                "timestamp":      row["timestamp"],
                "soil_pct":       row["soil_pct"],
                "lux":            row["lux"],
                "temp_c":         row["temp_c"],
                "humidity_pct":   row["humidity_pct"],
                "soil_drop_rate": row["soil_drop_rate"],
                "alerts":         alerts,
            })

        snapshot = {
            "generated_at": datetime.now().isoformat(),
            "readings":     readings,
        }

        # Write atomically: temp file → rename
        dir_ = os.path.dirname(os.path.abspath(SNAPSHOT_PATH)) or "."
        with tempfile.NamedTemporaryFile("w", dir=dir_, suffix=".tmp", delete=False) as f:
            json.dump(snapshot, f)
            tmp_path = f.name
        os.replace(tmp_path, SNAPSHOT_PATH)
        print(f"📸 Snapshot written — {len(readings)} readings")
    except Exception as e:
        print(f"⚠️  Snapshot write failed: {e}")

@app.route("/event", methods=["POST"])
def receive_event():
    payload = request.get_json(force=True)

    if payload.get("type") == "startup":
        print(f"🚀 Pico online — {payload.get('timestamp')}")
        return jsonify({"ok": True})

    r      = payload.get("readings", {})
    alerts = payload.get("alerts", [])

    with get_db() as conn:
        conn.execute("""
            INSERT INTO events
              (received_at, timestamp, plant, status,
               soil_raw, soil_pct, lux, temp_c, humidity_pct, soil_drop_rate,
               alerts_json, raw_payload)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().isoformat(),
            payload.get("timestamp"),
            payload.get("plant"),
            payload.get("status"),
            r.get("soil_raw"),
            r.get("soil_moisture_pct"),
            r.get("lux"),
            r.get("temp_c"),
            r.get("humidity_pct"),
            r.get("soil_drop_rate"),
            json.dumps(alerts),
            json.dumps(payload)
        ))

    print(f"📥 {payload.get('timestamp')} | {payload.get('plant')} | "
          f"soil {r.get('soil_moisture_pct')}% | alerts: {[a['trigger'] for a in alerts]}")
    write_snapshot()
    return jsonify({"ok": True})

@app.route("/snapshot", methods=["GET"])
def regenerate_snapshot():
    """Manually regenerate plant_data_snapshot.json on demand."""
    write_snapshot()
    return jsonify({"ok": True, "generated_at": datetime.now().isoformat()})

@app.route("/")
def index():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM events
            WHERE timestamp NOT LIKE 'nosync%'
            ORDER BY received_at DESC
            LIMIT 50
        """).fetchall()
    return render_template_string(UI_TEMPLATE, rows=rows)

UI_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>Plant Nanny</title>
<style>
  body { font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }
  h1 { font-weight: 500; margin-bottom: 4px; }
  p.sub { color: #888; font-size: 13px; margin-top: 0; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #e0e0e0; color: #666; font-weight: 500; }
  td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 4px; margin-right: 3px; }
  .ok { background: #e8f5e9; color: #2e7d32; }
  .alert { background: #fff3e0; color: #b45309; }
  .warn { background: #fef9c3; color: #854d0e; }
  .critical { background: #fee2e2; color: #991b1b; }
  .info { background: #e0f2fe; color: #0369a1; }
  .ts { color: #999; font-size: 12px; }
  .none { color: #ccc; }
</style>
</head>
<body>
<h1>🌿 Plant Nanny</h1>
<p class="sub">Last 50 readings — refreshes every 60 seconds</p>

<table>
  <thead>
    <tr>
      <th>Time</th>
      <th>Soil</th>
      <th>Light</th>
      <th>Temp</th>
      <th>Humidity</th>
      <th>Drop rate</th>
      <th>Alerts</th>
    </tr>
  </thead>
  <tbody>
  {% for row in rows %}
    <tr>
      <td class="ts">{{ row['timestamp'] }}</td>
      <td>
        {% if row['soil_pct'] %}
          {% if row['soil_pct'] < 35 %}
            <span style="color:#dc2626">{{ row['soil_pct'] }}%</span>
          {% elif row['soil_pct'] > 70 %}
            <span style="color:#2563eb">{{ row['soil_pct'] }}%</span>
          {% else %}
            <span style="color:#16a34a">{{ row['soil_pct'] }}%</span>
          {% endif %}
        {% else %}<span class="none">—</span>{% endif %}
      </td>
      <td>{{ row['lux'] if row['lux'] else '—' }} {% if row['lux'] %}lux{% endif %}</td>
      <td>{{ row['temp_c'] if row['temp_c'] else '—' }} {% if row['temp_c'] %}°C{% endif %}</td>
      <td>{{ row['humidity_pct'] if row['humidity_pct'] else '—' }} {% if row['humidity_pct'] %}%{% endif %}</td>
      <td>
        {% if row['soil_drop_rate'] %}
          {{ row['soil_drop_rate'] }}
        {% else %}
          <span class="none">—</span>
        {% endif %}
      </td>
      <td>
        {% if row['alerts_json'] %}
          {% set alerts = row['alerts_json'] | fromjson %}
          {% if alerts %}
            {% for a in alerts %}
              <span class="badge {{ a['severity'] }}">{{ a['trigger'] }}</span>
            {% endfor %}
          {% else %}
            <span class="badge ok">ok</span>
          {% endif %}
        {% endif %}
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</body>
</html>
"""

import json as _json
app.jinja_env.filters['fromjson'] = _json.loads

if __name__ == "__main__":
    init_db()
    print("🌿 Plant Nanny server running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)