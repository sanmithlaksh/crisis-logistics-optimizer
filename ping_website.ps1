# Set your live URL here
$URL = "https://crisis-logistics-optimizer.onrender.com"

# Ping interval (10 minutes = 600 seconds)
$IntervalSeconds = 600

Write-Host "Starting keep-alive ping service for: $URL" -ForegroundColor Cyan
Write-Host "Pinging every $($IntervalSeconds / 60) minutes. Press Ctrl+C to stop.`n" -ForegroundColor Yellow

while ($true) {
    try {
        $CurrentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        # Send a HEAD request to minimize bandwidth
        $Response = Invoke-WebRequest -Uri $URL -Method Head -UseBasicParsing -ErrorAction Stop
        Write-Host "[$CurrentTime] Ping sent. Server response status: $($Response.StatusCode)" -ForegroundColor Green
    }
    catch {
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Ping failed: $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds $IntervalSeconds
}
