param(
    [Parameter(Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]]$Usernames
)

if (-not $Usernames -or $Usernames.Count -eq 0) {
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host "            Sherlock OSINT Username Hunter              " -ForegroundColor Yellow
    Write-Host "========================================================" -ForegroundColor Cyan
    $inputUser = Read-Host "Enter username to search (ادخل اسم المستخدم)"
    if ([string]::IsNullOrWhiteSpace($inputUser)) {
        Write-Warning "No username entered. Exiting."
        exit
    }
    $Usernames = @($inputUser)
}

$ResultsDir = Join-Path $PSScriptRoot "results"
if (!(Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir | Out-Null
}

$firstUser = $Usernames[0]
$OutputPath = Join-Path $ResultsDir "result_$firstUser"

Write-Host "`n[*] Scanning for: $($Usernames -join ' ')..." -ForegroundColor Cyan
sherlock --csv --xlsx --output $OutputPath --print-found $Usernames

Write-Host "`n[*] Done! Results saved in: $ResultsDir" -ForegroundColor Green
Read-Host "Press Enter to exit"
