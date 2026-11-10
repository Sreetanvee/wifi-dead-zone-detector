from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import io
import os
import platform

from flask import Flask, Response, jsonify, render_template_string, request

app = Flask(__name__)
THRESHOLD = -75
readings = []
survey_state = {"active": False, "location": ""}

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Wi-Fi Signal Survey</title>
  <style>
    *{box-sizing:border-box}body{font:16px/1.55 Inter,Segoe UI,system-ui,sans-serif;max-width:960px;margin:0 auto;padding:34px 22px 60px;background:linear-gradient(135deg,#eef4ff,#f8fafc 55%,#eaf8f4);color:#17243a}
    h1{color:#102b4e;font-size:clamp(2rem,5vw,3.2rem);letter-spacing:-.04em;margin:0 0 6px}.muted{color:#60718a}.card{background:rgba(255,255,255,.95);padding:26px 30px;border:1px solid #e3eaf3;border-radius:18px;box-shadow:0 12px 32px rgba(31,57,88,.08);margin:20px 0}h2{font-size:1.35rem;margin:0 0 12px;color:#203754}
    .status{padding:14px 16px;border-radius:12px;background:#edf4fb;margin:18px 0}.status.good{background:#e9f7ef;color:#17653a}.status.warn{background:#fff3e7;color:#944200}.pill{display:inline-block;background:#e7edf5;border-radius:99px;padding:3px 10px;font-size:.9rem;margin-left:8px}code{background:#edf2f8;padding:2px 6px;border-radius:5px}
    button{font:inherit;padding:11px 15px;border:0;border-radius:10px;background:linear-gradient(135deg,#1767b1,#2053a0);color:white;font-weight:650;cursor:pointer;box-shadow:0 4px 10px #1767b133}button:hover{filter:brightness(1.08)}table{border-collapse:collapse;width:100%;margin-top:14px}td,th{text-align:left;padding:12px 10px;border-bottom:1px solid #e5ebf2}th{color:#60718a;font-size:.9rem}tr:hover td{background:#f7faff}.goodText{color:#16804a;font-weight:650}.warnText{color:#b34c00;font-weight:650}
    @media(max-width:650px){body{padding:22px 14px}.card{padding:20px 17px;overflow-x:auto}td,th{padding:9px 5px;font-size:.9rem}}
  </style>
</head>
<body>
  <h1>Wi-Fi Signal Survey</h1>
  <p class="muted">Measure the signal from the Wi-Fi network this Windows laptop is connected to, and record its strength by room.</p>
  <section class="card">
    <h2>Measure this room</h2>
    <p>Enter a room label, then start the survey. The Windows sensor reads the connected Wi-Fi adapter automatically every five seconds while the survey is active.</p>
    <form id="survey-form"><input id="location" name="location" placeholder="Room name (for example, Bedroom)" required><button type="submit">Start survey</button><button id="stop" type="button" disabled>Stop survey</button></form>
    <div id="survey-status" class="status">Survey stopped. Start the sensor with Start Demo before measuring.</div>
    <div id="live" class="status">Waiting for a measurement…</div>
    <p class="muted">RSSI means received Wi-Fi signal strength, measured in dBm. Values are negative; closer to 0 is stronger. This demo marks −75 dBm or weaker as a weak-signal area. The cutoff is a simple survey rule, not a universal Wi-Fi standard.</p>
  </section>
  <section class="card">
    <h2>Survey readings</h2>
    <button onclick="downloadCsv()">Download CSV</button>
    <table><thead><tr><th>Time (UTC)</th><th>Location label</th><th>RSSI</th><th>Status</th><th>Source</th></tr></thead><tbody id="rows"></tbody></table>
    <p id="empty" class="muted"></p>
  </section>
  <script>
    async function refresh(){
      try{
        const d=await (await fetch('/api/readings')).json();
        const survey=await (await fetch('/api/survey/status')).json();
        document.querySelector('#stop').disabled=!survey.active;
        document.querySelector('#survey-status').textContent=survey.active?`Survey active in ${survey.location}. Press Stop survey to finish.`:'Survey stopped.';
        const latest=d.readings[d.readings.length-1];
        const live=document.querySelector('#live');
        if(latest){live.className='status '+(latest.dead_zone?'warn':'good');live.textContent=`Latest: ${latest.rssi} dBm at “${latest.location}” — ${latest.dead_zone?'Weak signal':'Signal above the demo threshold'} · ${latest.time}`}
        const body=document.querySelector('#rows');body.replaceChildren();
        for(const x of [...d.readings].reverse()){
          const tr=document.createElement('tr');
          for(const value of [x.time,x.location,`${x.rssi} dBm`]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td)}
          const status=document.createElement('td');status.textContent=x.dead_zone?'Weak signal':'Above threshold';status.className=x.dead_zone?'warnText':'goodText';tr.appendChild(status);
          const source=document.createElement('td');source.textContent=x.source;tr.appendChild(source);body.appendChild(tr);
        }
        document.querySelector('#empty').textContent=d.readings.length?'':'No measurements yet. Start the Windows sensor agent while connected to Wi-Fi.';
      }catch(e){document.querySelector('#live').textContent='Could not reach the app API.'}
    }
    document.querySelector('#survey-form').onsubmit=async event=>{event.preventDefault();const room=document.querySelector('#location').value.trim();const r=await fetch('/api/survey/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:room})});const data=await r.json();document.querySelector('#survey-status').textContent=data.error||`Survey started in ${room}.`;refresh()};
    document.querySelector('#stop').onclick=async()=>{await fetch('/api/survey/stop',{method:'POST'});refresh()};
    function downloadCsv(){location.href='/api/readings.csv'}
    refresh();setInterval(refresh,3000);
  </script>
</body>
</html>"""


@dataclass
class Reading:
    time: str
    location: str
    rssi: int
    dead_zone: bool
    source: str


def record_reading(location, rssi, source):
    reading = Reading(
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        location,
        rssi,
        rssi <= THRESHOLD,
        source,
    )
    readings.append(reading)
    del readings[:-500]
    return reading


@app.get("/")
def home():
    return render_template_string(PAGE)


@app.get("/health")
def health():
    return jsonify(status="ok", service="wifi-dead-zone-detector")


@app.get("/api/readings")
def get_readings():
    return jsonify(threshold=THRESHOLD, readings=[asdict(x) for x in readings])


@app.get("/api/survey/status")
def get_survey_status():
    return jsonify(survey_state)


@app.post("/api/survey/start")
def start_survey():
    data = request.get_json(silent=True) or {}
    location = str(data.get("location", "")).strip()
    if not location:
        return jsonify(error="Enter a room label first."), 400
    survey_state.update(active=True, location=location[:120])
    return jsonify(survey_state)


@app.post("/api/survey/stop")
def stop_survey():
    survey_state["active"] = False
    return jsonify(survey_state)


@app.post("/api/sensor/readings")
def add_sensor_reading():
    if not survey_state["active"]:
        return jsonify(error="Start the room survey first."), 409
    data = request.get_json(silent=True) or {}
    try:
        rssi = int(data.get("rssi"))
    except (TypeError, ValueError):
        return jsonify(error="Sensor RSSI must be an integer"), 400
    if not -100 <= rssi <= 0:
        return jsonify(error="Sensor RSSI is outside the expected range"), 400
    reading = record_reading(survey_state["location"], rssi, "Windows Wi-Fi adapter")
    return jsonify(asdict(reading)), 201


@app.post("/api/readings")
def add_reading():
    data = request.get_json(silent=True) or {}
    location = str(data.get("location", "")).strip()
    try:
        rssi = int(data.get("rssi"))
    except (TypeError, ValueError):
        return jsonify(error="RSSI must be an integer from -100 to 0 dBm"), 400
    if not location:
        return jsonify(error="Location label is required"), 400
    if not -100 <= rssi <= 0:
        return jsonify(error="RSSI must be between -100 and 0 dBm"), 400
    source = str(data.get("source", "Manual API entry"))[:80]
    reading = record_reading(location, rssi, source)
    return jsonify(asdict(reading)), 201


@app.get("/api/readings.csv")
def export_csv():
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=["time", "location", "rssi", "dead_zone", "source"])
    writer.writeheader()
    writer.writerows(asdict(x) for x in readings)
    return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=wifi-readings.csv"})


@app.get("/api/environment")
def environment():
    return jsonify(python=platform.python_version(), platform=platform.platform(), docker=os.path.exists("/.dockerenv"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
