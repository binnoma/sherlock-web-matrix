Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         Sherlock OSINT Web - Server Launcher           " -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "`n[*] Starting web server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "[*] The browser will open automatically." -ForegroundColor Gray
Write-Host "[*] Press Ctrl+C to stop the server.`n" -ForegroundColor Gray

python "$PSScriptRoot\web_app.py"
