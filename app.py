from dataclasses import dataclass, asdict
from datetime import datetime
import csv
import io
import json
import platform
import subprocess

from flask import Flask, Response, jsonify, render_template_string, request

app = Flask(__name__)

PAGE = """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>Wi-Fi Dead Zone Detector</title><style>body{font:16px/1.55 Inter,Segoe UI,system-ui,sans-serif;max-width:920px;margin:0 auto;padding:34px 22px 60px;background:linear-gradient(135deg,#eef4ff,#f8fafc 55%,#eaf8f4);color:#17243a}h1{color:#102b4e;font-size:clamp(2rem,5vw,3.2rem);letter-spacing:-.04em;margin:0 0 6px}.muted{color:#60718a}.card{background:rgba(255,255,255,.94);padding:26px 30px;border:1px solid #e3eaf3;border-radius:18px;box-shadow:0 12px 32px rgba(31,57,88,.08);margin:20px 0}h2{font-size:1.35rem;margin:0 0 18px;color:#203754}input,button{font:inherit;padding:12px 15px;margin:5px;border:1px solid #cbd7e5;border-radius:10px}input:focus{outline:3px solid #c8dcfa;border-color:#4384d2}button{background:linear-gradient(135deg,#1767b1,#2053a0);color:white;border:0;font-weight:650;cursor:pointer;box-shadow:0 4px 10px #1767b133}button:hover{filter:brightness(1.08);transform:translateY(-1px)}.good{color:#16804a;font-weight:600}.warn{color:#b34c00;font-weight:600}table{border-collapse:collapse;width:100%;margin-top:14px}td,th{text-align:left;padding:12px 10px;border-bottom:1px solid #e5ebf2}th{color:#60718a;font-size:.9rem}tr:hover td{background:#f7faff}#message{color:#16804a;font-weight:600}form{display:flex;flex-wrap:wrap;gap:5px}form input:first-child{flex:1;min-width:190px} @media(max-width:600px){body{padding:22px 14px}.card{padding:20px 17px}td,th{padding:9px 5px;font-size:.9rem}}</style></head><body><h1>Wi-Fi Dead Zone Detector</h1><p class='muted'>Record Wi-Fi signal strength at different locations and flag weak coverage areas.</p><div class='card'><h2>Add a reading</h2><form id='form'><input name='location' placeholder='Location (e.g. Room 204)' required><input name='rssi' type='number' min='-100' max='0' placeholder='RSSI dBm (e.g. -72)' required><button>Save reading</button></form><p id='message'></p><p>Threshold: <b id='threshold'></b> dBm or weaker is considered a dead zone.</p></div><div class='card'><h2>Survey results</h2><button onclick='downloadCsv()'>Download CSV</button><table><thead><tr><th>Time (UTC)</th><th>Location</th><th>RSSI</th><th>Status</th></tr></thead><tbody id='rows'></tbody></table><p id='empty' class='muted'></p></div><script>async function refresh(){let d=await (await fetch('/api/readings')).json();document.querySelector('#threshold').textContent=d.threshold;document.querySelector('#rows').innerHTML=d.readings.map(x=>`<tr><td>${x.time}</td><td>${x.location}</td><td>${x.rssi} dBm</td><td class='${x.dead_zone?'warn':'good'}'>${x.dead_zone?'Weak signal':'Coverage OK'}</td></tr>`).join('');document.querySelector('#empty').textContent=d.readings.length?'':'No readings yet. Add one above.'}document.querySelector('#form').onsubmit=async e=>{e.preventDefault();let f=new FormData(e.target);let r=await fetch('/api/readings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:f.get('location'),rssi:Number(f.get('rssi'))})});let d=await r.json();document.querySelector('#message').textContent=d.error||'Reading saved';e.target.reset();refresh()};function downloadCsv(){location.href='/api/readings.csv'}refresh();</script></body></html>"""

@dataclass
class Reading:
    time: str
    location: str
    rssi: int
    dead_zone: bool

readings = []
THRESHOLD = -75

@app.get('/')
def home():
    return render_template_string(PAGE)

@app.get('/health')
def health():
    return jsonify(status='ok', service='wifi-dead-zone-detector')

@app.get('/api/readings')
def get_readings():
    return jsonify(threshold=THRESHOLD, readings=[asdict(x) for x in readings])

@app.post('/api/readings')
def add_reading():
    data = request.get_json(silent=True) or {}
    location = str(data.get('location', '')).strip()
    try:
        rssi = int(data.get('rssi'))
    except (TypeError, ValueError):
        return jsonify(error='RSSI must be an integer from -100 to 0 dBm'), 400
    if not location:
        return jsonify(error='Location is required'), 400
    if not -100 <= rssi <= 0:
        return jsonify(error='RSSI must be between -100 and 0 dBm'), 400
    reading = Reading(datetime.utcnow().replace(microsecond=0).isoformat() + 'Z', location, rssi, rssi <= THRESHOLD)
    readings.append(reading)
    return jsonify(asdict(reading)), 201

@app.get('/api/readings.csv')
def export_csv():
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=['time','location','rssi','dead_zone'])
    writer.writeheader()
    writer.writerows(asdict(x) for x in readings)
    return Response(stream.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=wifi-readings.csv'})

@app.get('/api/environment')
def environment():
    return jsonify(python=platform.python_version(), platform=platform.platform(), docker=subprocess.run(['sh','-c','test -f /.dockerenv && echo yes || echo no'],capture_output=True,text=True).stdout.strip())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

