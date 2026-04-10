param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$Question = "Does Michelin structurally outperform peers on margins?"
)

$ErrorActionPreference = "Stop"

Write-Host "== Local API Smoke Test ==" -ForegroundColor Cyan
Write-Host "API Base: $ApiBase"

function Invoke-JsonPost {
    param(
        [string]$Uri,
        [hashtable]$Body
    )
    $json = $Body | ConvertTo-Json -Depth 8
    return Invoke-RestMethod -Uri $Uri -Method Post -ContentType "application/json" -Body $json
}

try {
    $health = Invoke-RestMethod -Uri "$ApiBase/health"
    Write-Host "[OK] /health status=$($health.status), model=$($health.model)" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] /health" -ForegroundColor Red
    throw
}

try {
    $p = Invoke-JsonPost -Uri "$ApiBase/search/patents" -Body @{ query = "ai"; max_results = 3 }
    Write-Host "[OK] /search/patents returned=$($p.returned)" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] /search/patents" -ForegroundColor Red
    throw
}

try {
    $t = Invoke-JsonPost -Uri "$ApiBase/search/transcripts" -Body @{ query = "Michelin 2025"; max_results = 2 }
    $preview = [string]$t.result
    if ($preview.Length -gt 120) { $preview = $preview.Substring(0, 120) + "..." }
    Write-Host "[OK] /search/transcripts preview=$preview" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] /search/transcripts" -ForegroundColor Red
    throw
}

try {
    $qa = Invoke-JsonPost -Uri "$ApiBase/qa" -Body @{ messages = @(@{ role = "user"; content = $Question }) }
    $a = [string]$qa.answer
    if ($a.Length -gt 140) { $a = $a.Substring(0, 140) + "..." }
    Write-Host "[OK] /qa answer preview=$a" -ForegroundColor Green
    Write-Host "     citations=$($qa.citations.Count), tool_trace=$($qa.tool_trace.Count)"
}
catch {
    $resp = $_.Exception.Response
    if ($resp -ne $null) {
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $detail = $reader.ReadToEnd()
        Write-Host "[WARN] /qa failed: $detail" -ForegroundColor Yellow
    }
    else {
        Write-Host "[WARN] /qa failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "Done." -ForegroundColor Cyan
