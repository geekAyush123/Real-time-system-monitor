# Distributed System Setup Guide - Master-Worker Architecture

## Architecture Overview

```
Worker Node 1 (PC 1)          Worker Node 2 (PC 2)          Worker Node N (PC N)
    |                              |                              |
    | Producer                     | Producer                     | Producer
    | (Collects Metrics)           | (Collects Metrics)           | (Collects Metrics)
    |                              |                              |
    +------------------------------+------------------------------+
                                   |
                                   v
                        Master Node (Main PC)
                                   |
                        +----------+----------+
                        |                     |
                    Kafka Broker          Redis Cache
                        |                     |
                        v                     v
                    Consumer ---------> SQLite Database
                        |
                        v
                Gradio Dashboard (UI)
                http://master-ip:7861
```

## Prerequisites

- All PCs must be on the same network
- Python 3.8+ installed on all machines
- Docker installed on Master Node
- Firewall ports opened: 9092 (Kafka), 6379 (Redis), 7861 (Dashboard)

---

## MASTER NODE SETUP (Main PC)

### Step 1: Get Master Node IP Address
```powershell
# On Windows
ipconfig

# Note down your IPv4 Address, e.g., 192.168.1.100
```

### Step 2: Update docker-compose.yml for Network Access
Edit `docker-compose.yml` and change Kafka advertised listeners:

```yaml
# Replace localhost with your Master IP
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://192.168.1.100:9092,PLAINTEXT_INTERNAL://kafka:29092
```

### Step 3: Start Infrastructure
```powershell
cd d:\real-time-monitoring-main\real-time-monitoring-main
docker-compose down
docker-compose up -d
```

### Step 4: Initialize Database
```powershell
python src/database.py
```

### Step 5: Start Consumer (Master Node)
```powershell
python src/simple_consumer.py
```
Keep this running in one terminal.

### Step 6: Start Dashboard (Master Node)
```powershell
python src/gradio_dashboard.py
```
Keep this running in another terminal.

Access Dashboard: `http://192.168.1.100:7861` (replace with your Master IP)

---

## WORKER NODE SETUP (Each Worker PC)

### Step 1: Copy Required Files to Worker Nodes
On each Worker PC, you need:
- `src/producer.py`
- `requirements.txt` (only need: psutil, kafka-python)

### Step 2: Install Dependencies on Worker Nodes
```powershell
pip install psutil kafka-python
```

### Step 3: Configure Producer on Worker Nodes
Edit `src/producer.py` and change:

```python
# Change from:
KAFKA_BROKER = 'localhost:9092'

# To Master Node's IP:
KAFKA_BROKER = '192.168.1.100:9092'  # Replace with actual Master IP
```

### Step 4: Run Producer on Each Worker Node
```powershell
python src/producer.py
```

Each worker will:
- Collect metrics from its own system
- Send data to Master Node's Kafka
- Use unique machine_id (auto-generated)

---

## FIREWALL CONFIGURATION

### On Master Node (Windows):
```powershell
# Allow Kafka port
New-NetFirewallRule -DisplayName "Kafka" -Direction Inbound -LocalPort 9092 -Protocol TCP -Action Allow

# Allow Redis port
New-NetFirewallRule -DisplayName "Redis" -Direction Inbound -LocalPort 6379 -Protocol TCP -Action Allow

# Allow Dashboard port
New-NetFirewallRule -DisplayName "Gradio Dashboard" -Direction Inbound -LocalPort 7861 -Protocol TCP -Action Allow
```

---

## TESTING THE SETUP

### 1. Test Kafka Connection from Worker Node
```python
# test_kafka.py on Worker Node
from kafka import KafkaProducer
import json

MASTER_IP = '192.168.1.100'  # Replace with your Master IP
producer = KafkaProducer(
    bootstrap_servers=[f'{MASTER_IP}:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send test message
producer.send('system_metrics', {'test': 'connection'})
producer.flush()
print("Test message sent successfully!")
```

### 2. Verify Data Flow
1. Start Master Node components (Consumer + Dashboard)
2. Start Producer on Worker Node 1
3. Start Producer on Worker Node 2
4. Open Dashboard: `http://master-ip:7861`
5. You should see metrics from multiple machines

---

## MONITORING MULTIPLE MACHINES

The dashboard will show:
- **Machine IDs**: Each worker has unique ID (machine_46, machine_47, etc.)
- **Aggregated Metrics**: Combined CPU, Memory usage across all nodes
- **Per-Machine Stats**: Dropdown to view individual machine metrics
- **Top Processes**: From all monitored machines

---

## TROUBLESHOOTING

### Worker can't connect to Master:
1. Check Master IP: `ipconfig` on Master
2. Ping Master from Worker: `ping 192.168.1.100`
3. Check firewall rules on Master
4. Verify Kafka is running: `docker ps` on Master

### Dashboard shows no data:
1. Verify Consumer is running on Master
2. Check Redis is running: `docker ps`
3. Check database exists: `data/system_metrics.db`

### Producer errors on Worker:
1. Verify KAFKA_BROKER IP is correct
2. Check network connectivity
3. Ensure Kafka port 9092 is accessible

---

## QUICK START CHECKLIST

### Master Node:
- [ ] Get Master IP address
- [ ] Update docker-compose.yml with Master IP
- [ ] Start Docker services (Kafka, Redis)
- [ ] Initialize database
- [ ] Start Consumer
- [ ] Start Gradio Dashboard
- [ ] Configure firewall

### Worker Node 1:
- [ ] Install Python + dependencies
- [ ] Copy producer.py
- [ ] Update KAFKA_BROKER to Master IP
- [ ] Run producer.py

### Worker Node 2:
- [ ] Install Python + dependencies
- [ ] Copy producer.py
- [ ] Update KAFKA_BROKER to Master IP
- [ ] Run producer.py

### Verification:
- [ ] Access Dashboard from any PC: `http://master-ip:7861`
- [ ] See metrics from all worker nodes
- [ ] Verify real-time updates

---

## SCALING TO MORE WORKERS

To add more worker nodes:
1. Copy producer.py to new PC
2. Update KAFKA_BROKER to Master IP
3. Run producer.py
4. No changes needed on Master Node!

Kafka and the consumer will automatically handle multiple producers.

---

## DEMO POINTS FOR MENTOR

1. **Architecture**: Show Master-Worker distributed setup
2. **Scalability**: Add/remove worker nodes dynamically
3. **Real-time**: Live metrics from multiple machines
4. **Centralized Monitoring**: Single dashboard for all nodes
5. **UI**: Professional Gradio interface with charts
6. **Technologies**: Kafka (distributed messaging), Redis (caching), Docker (containerization)

---

## Network Topology Example

```
Network: 192.168.1.0/24

Master Node:   192.168.1.100
  - Kafka:     192.168.1.100:9092
  - Redis:     192.168.1.100:6379
  - Dashboard: 192.168.1.100:7861

Worker Node 1: 192.168.1.101
  - Producer → connects to 192.168.1.100:9092

Worker Node 2: 192.168.1.102
  - Producer → connects to 192.168.1.100:9092

Worker Node 3: 192.168.1.103
  - Producer → connects to 192.168.1.100:9092
```

Access dashboard from ANY device on network: `http://192.168.1.100:7861`
