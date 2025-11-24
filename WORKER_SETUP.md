# Worker Node Setup Guide

## Quick Start - How Worker Nodes Send Data to Master

### Prerequisites
- Master Node and Worker Nodes on **same network**
- Python 3.8+ installed on all machines
- Network connectivity between machines

---

## 🖥️ MASTER NODE SETUP (Your Main PC)

### Step 1: Get Master IP Address
```powershell
ipconfig
```
Look for **IPv4 Address** (e.g., `192.168.1.100`)

### Step 2: Update Kafka Configuration
Edit `docker-compose.yml`:
```yaml
kafka:
  environment:
    # Replace localhost with YOUR Master IP
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://192.168.1.100:9092,PLAINTEXT_INTERNAL://kafka:29092
```

### Step 3: Restart Docker Services
```powershell
docker-compose down
docker-compose up -d
```

### Step 4: Open Firewall (Run as Administrator)
```powershell
# Allow Kafka port
New-NetFirewallRule -DisplayName "Kafka-Monitor" -Direction Inbound -LocalPort 9092 -Protocol TCP -Action Allow

# Allow Dashboard port
New-NetFirewallRule -DisplayName "Dashboard-Monitor" -Direction Inbound -LocalPort 7861 -Protocol TCP -Action Allow
```

### Step 5: Start Services on Master
```powershell
# Terminal 1 - Consumer
python src/simple_consumer.py

# Terminal 2 - Dashboard
python src/multi_machine_dashboard.py
```

Dashboard will be accessible at: `http://YOUR-MASTER-IP:7861`

---

## 💻 WORKER NODE SETUP (Other PCs)

### Step 1: Copy Required Files
Copy these files to each Worker PC:
```
producer.py
setup_worker.py  (automated setup script)
```

Or just copy the entire `src` folder.

### Step 2: Run Automated Setup
```powershell
python setup_worker.py
```

It will:
- Ask for Master IP
- Test connection
- Configure producer.py automatically
- Install dependencies
- Verify setup

### Step 3: Start Producer
```powershell
python producer.py
```

**Done!** Worker will now send metrics to Master.

---

## 🔧 MANUAL WORKER SETUP (Alternative)

If automated setup doesn't work:

### 1. Install Dependencies
```powershell
pip install psutil kafka-python
```

### 2. Edit producer.py
Open `producer.py` and change line 9:
```python
# From:
KAFKA_BROKER = 'localhost:9092'

# To (use your actual Master IP):
KAFKA_BROKER = '192.168.1.100:9092'
```

### 3. Run Producer
```powershell
python producer.py
```

---

## ✅ VERIFICATION

### On Master Dashboard, you should see:
```
🖥️ Connected Machines: 3
*Only showing machines active in last 2 minutes*

machine_46 (Master PC)
- CPU: Avg 5.2% | Max 12.3%
- Memory: Avg 65.5% | Max 78.2%

machine_47 (Worker 1)
- CPU: Avg 8.1% | Max 15.7%
- Memory: Avg 45.2% | Max 52.8%

machine_48 (Worker 2)
- CPU: Avg 6.5% | Max 11.2%
- Memory: Avg 51.3% | Max 58.9%
```

### Each machine shows as a different colored line in charts.

---

## 🔍 TROUBLESHOOTING

### Worker can't connect to Master:

**1. Check Master IP**
```powershell
# On Master PC
ipconfig
```

**2. Test Network Connection**
```powershell
# On Worker PC
ping 192.168.1.100
```

**3. Check Firewall**
- On Master, ensure port 9092 is open
- Windows Firewall → Allow app → Add port 9092

**4. Verify Kafka is Running**
```powershell
# On Master PC
docker ps
```
Should show `kafka` container running.

**5. Test Kafka Connection**
```python
# On Worker PC - test_kafka.py
from kafka import KafkaProducer
import json

MASTER_IP = '192.168.1.100'  # Your Master IP

producer = KafkaProducer(
    bootstrap_servers=[f'{MASTER_IP}:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('system_metrics', {'test': 'hello from worker'})
producer.flush()
print("✅ Connection successful!")
```

---

## 📊 ACCESSING DASHBOARD

### From Master PC:
```
http://localhost:7861
```

### From Worker PCs or any device on network:
```
http://192.168.1.100:7861
```
(Replace with your actual Master IP)

---

## 🚀 ADDING MORE WORKERS

To add more worker nodes:
1. Copy `producer.py` to new PC
2. Run `setup_worker.py` (or manually configure)
3. Start producer
4. New machine automatically appears on dashboard!

**No changes needed on Master Node!**

---

## 📝 NETWORK TOPOLOGY EXAMPLE

```
Network: 192.168.1.0/24

Master Node:     192.168.1.100
  ├─ Kafka:      port 9092
  ├─ Redis:      port 6379
  ├─ Consumer:   running
  └─ Dashboard:  port 7861

Worker 1:        192.168.1.101
  └─ Producer → sends to 192.168.1.100:9092

Worker 2:        192.168.1.102
  └─ Producer → sends to 192.168.1.100:9092

Worker 3:        192.168.1.103
  └─ Producer → sends to 192.168.1.100:9092
```

---

## 🎯 DATA FLOW

```
Worker Node → Producer → Kafka (Master) → Consumer (Master) → Redis/SQLite → Dashboard
```

Each worker independently sends its metrics to Kafka on Master.
Consumer processes all messages and stores in database.
Dashboard reads from database and shows all machines together.

---

## 🔐 SECURITY NOTE

This setup is for **local network only**. 

For production:
- Add authentication to Kafka
- Use SSL/TLS for encryption
- Set up proper firewall rules
- Use VPN for remote workers
