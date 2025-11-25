<div align="center">

# Real-Time Multi-Computer System Monitoring & Anomaly Detection

Monitor multiple machines in real-time with a lightweight master–worker architecture. Collect CPU, Memory, Disk and Network metrics, store them, visualize trends, and automatically flag anomalies using IsolationForest.

**Technologies:** Python, Kafka, Redis, SQLite, Gradio, (Optional: Spark / Streamlit)  
**Core Files:** `producer.py`, `simple_consumer.py`, `multi_machine_dashboard.py`  
**Anomaly Engine:** IsolationForest (scikit-learn)

</div>

---

##  Key Features

- Multi-machine monitoring (workers stream to master Kafka)  
- Real-time dashboards (Gradio UI with per-machine & aggregated views)  
- Lightweight storage (SQLite + optional Redis for caching)  
- Plug & play producers (just point at master IP)  
- Automatic machine identification (`machine_<n>`)  
- Anomaly detection tab (IsolationForest: CPU/Memory + I/O/Network deltas)  
- Extensible design (add alerts, predictive models, Spark streaming)  
- Simple setup scripts (`setup_worker.py`, PowerShell helpers)  

---
## ARCHITECTURE OVERVIEW 
<img width="2291" height="4462" alt="deepseek_mermaid_20251125_c4fc17" src="https://github.com/user-attachments/assets/5bfd092e-1007-4b90-8890-641c7c408220" />


```

For advanced batch / windowed analytics you can enable `streaming.py` (PySpark Structured Streaming), but the default flow works without Spark.

---

##  Project Structure (Relevant Parts)

```
src/
  producer.py              # Collect & send metrics to Kafka
  simple_consumer.py       # Consumes metrics, stores in SQLite
  multi_machine_dashboard.py # Gradio multi-machine + anomaly UI
  gradio_dashboard.py      # Single-machine legacy dashboard
  database.py              # Initializes SQLite schema
  cleanup_database.py      # Maintenance script
  setup_worker.py          # Interactive worker setup utility
  alerts.py                # (Optional) local notification logic
data/system_metrics.db     # SQLite database
docker-compose.yml         # Kafka + Redis services
```

---

##  Requirements

Install Python 3.8+ then:

```bash
pip install -r requirements.txt
```

Ensure Docker is installed (for Kafka & optional Redis). If using Spark features: install Java + Spark distribution.

---

##  Quick Start (Single Machine Demo)

```bash
# 1. Start Kafka + Redis
docker-compose up -d

# 2. Init DB
python src/database.py

# 3. Start consumer (store metrics)
python src/simple_consumer.py

# 4. Start dashboard (multi-machine capable)
python src/multi_machine_dashboard.py

# 5. Start local producer (same machine)
python src/producer.py
```

Visit: `http://localhost:7863`  → You will see one machine. Add more producers (even on same machine) to simulate additional hosts.

---

##  Multi-Computer Setup (Master + Workers)

### Master Node Steps
1. Find IP: `ipconfig` (choose LAN IPv4, e.g. `192.168.1.101`).  
2. Edit `docker-compose.yml` → set `KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://<MASTER_IP>:9092,...`  
3. Restart services: `docker-compose down && docker-compose up -d`.  
4. Open firewall ports (Windows examples):  
   - 9092 (Kafka), 7863 (Dashboard), 6379 (Redis optional)  
5. Initialize DB: `python src/database.py`  
6. Run consumer: `python src/simple_consumer.py`  
7. Run dashboard: `python src/multi_machine_dashboard.py`  

### Worker Node Steps
Option A (Automated): Copy `producer.py` + `setup_worker.py`, then:  
```bash
python setup_worker.py   # enter MASTER_IP when prompted
python producer.py
```
Option B (Manual):  
```bash
pip install psutil kafka-python
# Edit inside producer.py
KAFKA_BROKER = '<MASTER_IP>:9092'
python producer.py
```

Open dashboard from any node: `http://<MASTER_IP>:7863`

---

##  Anomaly Detection (IsolationForest)

The dashboard builds a feature set per machine using:
- CPU %, Memory %
- Δ Disk Read / Write bytes
- Δ Net Sent / Received bytes

It keeps a sliding window (~last 50 samples per machine) and trains / retrains an `IsolationForest` when data size changes significantly. Output:
- Scatter: CPU vs Memory, color-coded (Red = anomaly)
- Summary: Latest machine state flag (🟢 Normal / 🔴 Anomalous) + raw decision score

### Tuning
Edit in `multi_machine_dashboard.py`:
```python
IsolationForest(n_estimators=120, contamination='auto', random_state=42)
```
You can set `contamination=0.05` to force ~5% anomaly rate or increase estimators for stability.

### Interpreting Scores
- More negative score → more isolated (potential issue)
- Frequent anomalies may indicate spikes: CPU saturation, memory pressure or abnormal I/O bursts

### Missing scikit-learn?
If not installed the Anomaly tab shows a warning. Install:
```bash
pip install scikit-learn
```

---

##  Troubleshooting

| Issue | Checks |
|-------|--------|
| Worker not appearing | Ping master, verify `KAFKA_BROKER` string, firewall port 9092 open |
| Dashboard empty | Confirm consumer running, DB file `data/system_metrics.db` exists |
| Port already in use | Change `server_port` in `multi_machine_dashboard.py` (e.g. 7864) |
| Kafka errors | Recreate containers, ensure advertised listener updated to actual IP |
| Anomaly tab blank | Not enough data yet (need several samples), or scikit-learn missing |

Quick Kafka test from worker:
```python
from kafka import KafkaProducer; import json
p = KafkaProducer(bootstrap_servers=['<MASTER_IP>:9092'], value_serializer=lambda v: json.dumps(v).encode())
p.send('system_metrics', {'test':'ok'}); p.flush(); print('Sent!')
```

---

## Scaling & Extensions

- Add PySpark (`streaming.py`) for window aggregations & heavy analytics.
- Increase Kafka partitions (`KAFKA_CREATE_TOPICS` env or admin script) for high producer counts.
- Swap SQLite for PostgreSQL / TimescaleDB for long-term multi-GB retention.
- Add authentication / SSL for Kafka if crossing untrusted networks.
- Integrate alert pipeline (email / Slack) triggered by anomaly flags.

---

##  Security Notes (Local Dev Focus)

Current setup is LAN-focused (no auth). For production:
- Enable Kafka SASL/SSL
- Restrict dashboard port via reverse proxy / auth
- Harden firewall rules (allow only known worker IPs)
- Use VPN or secure tunnel for remote workers

---

##  Contributing

PRs welcome for: additional features (Prometheus exporter, process correlation, GPU metrics, ML forecasting). Keep changes modular and documented.




