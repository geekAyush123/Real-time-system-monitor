"""
Worker Node Quick Setup Script
Run this on each Worker PC to configure and start the producer
"""

import sys

print("\n" + "="*60)
print("WORKER NODE SETUP - Real-Time Monitoring")
print("="*60 + "\n")

# Get Master IP
master_ip = input("Enter Master Node IP address (e.g., 192.168.1.100): ").strip()

if not master_ip:
    print("❌ Master IP is required!")
    sys.exit(1)

print(f"\n📡 Master Node IP: {master_ip}")

# Test connection
print("\n🔍 Testing connection to Master Node...")
import os
response = os.system(f"ping -n 2 {master_ip} > nul 2>&1")

if response == 0:
    print(f"✅ Master Node {master_ip} is reachable!")
else:
    print(f"❌ Cannot reach Master Node at {master_ip}")
    print("   Please check:")
    print("   1. Master Node is on and connected to network")
    print("   2. Both PCs are on same network")
    print("   3. IP address is correct (run 'ipconfig' on Master)")
    cont = input("\n   Continue anyway? (y/n): ")
    if cont.lower() != 'y':
        sys.exit(1)

# Update producer.py
print("\n📝 Configuring producer.py...")
try:
    with open('producer.py', 'r') as f:
        content = f.read()
    
    # Replace KAFKA_BROKER line
    import re
    updated_content = re.sub(
        r"KAFKA_BROKER = ['\"].*?['\"]",
        f"KAFKA_BROKER = '{master_ip}:9092'",
        content
    )
    
    with open('producer.py', 'w') as f:
        f.write(updated_content)
    
    print(f"✅ producer.py configured to send data to {master_ip}:9092")
    
except FileNotFoundError:
    print("❌ producer.py not found in current directory!")
    print("   Please make sure you copied producer.py to this folder.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error updating producer.py: {e}")
    sys.exit(1)

# Check dependencies
print("\n📦 Checking dependencies...")
try:
    import psutil
    print("✅ psutil installed")
except ImportError:
    print("⚠️  psutil not installed. Installing...")
    os.system("pip install psutil")

try:
    import kafka
    print("✅ kafka-python installed")
except ImportError:
    print("⚠️  kafka-python not installed. Installing...")
    os.system("pip install kafka-python")

print("\n" + "="*60)
print("✅ WORKER NODE SETUP COMPLETE!")
print("="*60)
print(f"\nThis worker will send metrics to: {master_ip}:9092")
print("\nTo start monitoring, run:")
print("    python producer.py")
print("\nThe worker will appear on the Master's dashboard as a new machine.")
print("="*60 + "\n")
