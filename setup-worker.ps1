# Worker Node Setup Script
# Run this on each Worker PC

param(
    [Parameter(Mandatory=$true)]
    [string]$MasterIP
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WORKER NODE SETUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Master Node IP: $MasterIP" -ForegroundColor Green

# Test connection to Master
Write-Host "`nTesting connection to Master Node..." -ForegroundColor Yellow
$testResult = Test-Connection -ComputerName $MasterIP -Count 2 -Quiet

if ($testResult) {
    Write-Host "✓ Master Node is reachable!" -ForegroundColor Green
} else {
    Write-Host "✗ Cannot reach Master Node at $MasterIP" -ForegroundColor Red
    Write-Host "Please check network connection and Master IP address." -ForegroundColor Red
    exit
}

# Update producer.py
Write-Host "`nUpdating producer.py with Master IP..." -ForegroundColor Yellow
$producerPath = "src\producer.py"

if (Test-Path $producerPath) {
    $content = Get-Content $producerPath -Raw
    $updatedContent = $content -replace "KAFKA_BROKER = 'localhost:9092'", "KAFKA_BROKER = '${MasterIP}:9092'"
    Set-Content -Path $producerPath -Value $updatedContent
    Write-Host "✓ producer.py updated successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ producer.py not found at $producerPath" -ForegroundColor Red
    exit
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  WORKER NODE READY!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "To start monitoring, run:" -ForegroundColor Yellow
Write-Host "python src\producer.py`n" -ForegroundColor Green

Write-Host "This worker will send metrics to:" -ForegroundColor White
Write-Host "Kafka Broker: ${MasterIP}:9092`n" -ForegroundColor Gray
