# Setup Script for Master Node
# Run this on your Master PC to get IP and instructions

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DISTRIBUTED MONITORING SETUP - MASTER NODE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Get IP Address
Write-Host "Step 1: Getting Master Node IP Address..." -ForegroundColor Yellow
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*"}).IPAddress | Select-Object -First 1

if ($ipAddress) {
    Write-Host "Master Node IP: $ipAddress" -ForegroundColor Green
} else {
    Write-Host "Could not auto-detect IP. Please run 'ipconfig' manually." -ForegroundColor Red
    exit
}

# Update docker-compose.yml
Write-Host "`nStep 2: Updating docker-compose.yml..." -ForegroundColor Yellow
$dockerComposePath = "docker-compose.yml"
if (Test-Path $dockerComposePath) {
    $content = Get-Content $dockerComposePath -Raw
    $updatedContent = $content -replace "PLAINTEXT://localhost:9092", "PLAINTEXT://${ipAddress}:9092"
    Set-Content -Path $dockerComposePath -Value $updatedContent
    Write-Host "docker-compose.yml updated successfully!" -ForegroundColor Green
} else {
    Write-Host "docker-compose.yml not found!" -ForegroundColor Red
}

# Firewall rules
Write-Host "`nStep 3: Setting up firewall rules..." -ForegroundColor Yellow
Write-Host "Creating firewall rules for Kafka, Redis, and Dashboard..." -ForegroundColor Gray

try {
    New-NetFirewallRule -DisplayName "Kafka-Monitoring" -Direction Inbound -LocalPort 9092 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    Write-Host "✓ Kafka port 9092 opened" -ForegroundColor Green
} catch {
    Write-Host "✗ Kafka rule already exists or needs admin rights" -ForegroundColor Yellow
}

try {
    New-NetFirewallRule -DisplayName "Redis-Monitoring" -Direction Inbound -LocalPort 6379 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    Write-Host "✓ Redis port 6379 opened" -ForegroundColor Green
} catch {
    Write-Host "✗ Redis rule already exists or needs admin rights" -ForegroundColor Yellow
}

try {
    New-NetFirewallRule -DisplayName "Gradio-Dashboard" -Direction Inbound -LocalPort 7861 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    Write-Host "✓ Dashboard port 7861 opened" -ForegroundColor Green
} catch {
    Write-Host "✗ Dashboard rule already exists or needs admin rights" -ForegroundColor Yellow
}

# Instructions
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "MASTER NODE (This PC):" -ForegroundColor Yellow
Write-Host "1. Start Docker services:" -ForegroundColor White
Write-Host "   docker-compose up -d`n" -ForegroundColor Gray

Write-Host "2. Initialize database:" -ForegroundColor White
Write-Host "   python src/database.py`n" -ForegroundColor Gray

Write-Host "3. Start consumer:" -ForegroundColor White
Write-Host "   python src/simple_consumer.py`n" -ForegroundColor Gray

Write-Host "4. Start dashboard:" -ForegroundColor White
Write-Host "   python src/gradio_dashboard.py`n" -ForegroundColor Gray

Write-Host "`nWORKER NODES (Other PCs):" -ForegroundColor Yellow
Write-Host "1. Install Python and dependencies:" -ForegroundColor White
Write-Host "   pip install psutil kafka-python`n" -ForegroundColor Gray

Write-Host "2. Edit src/producer.py and change:" -ForegroundColor White
Write-Host "   KAFKA_BROKER = '$ipAddress:9092'`n" -ForegroundColor Gray

Write-Host "3. Run producer on each worker:" -ForegroundColor White
Write-Host "   python src/producer.py`n" -ForegroundColor Gray

Write-Host "`nACCESS DASHBOARD:" -ForegroundColor Yellow
Write-Host "From any device on network: http://${ipAddress}:7861" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Configuration saved! Ready to start." -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan
