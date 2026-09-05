# لوحة مراقبة نظام إدارة الذاكرة
# احفظها كـ check_memory_system.ps1

param(
    [string]$Project = "system_validation_test"
)

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🧠 لوحة مراقبة نظام إدارة الذاكرة  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan

$p = "projects/$Project"

# 1. فحص الملفات
$files = @{
    "session_digest.md" = "$p/session_digest.md"
    ".session_state.json" = "$p/.session_state.json"
    "master_plan.md" = "$p/master_plan.md"
}

Write-Host "`n📁 حالة الملفات:" -ForegroundColor Yellow
foreach ($name in $files.Keys) {
    if (Test-Path $files[$name]) {
        $size = (Get-Item $files[$name]).Length
        Write-Host "  ✅ $name ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $name (مفقود)" -ForegroundColor Red
    }
}

# 2. فحص digest
$digest = "$p/session_digest.md"
if (Test-Path $digest) {
    $lines = (Get-Content $digest).Count
    if ($lines -le 100) {
        Write-Host "`n📊 أسطر Digest: $lines ✅" -ForegroundColor Green
    } else {
        Write-Host "`n📊 أسطر Digest: $lines ⚠️ تجاوز الحد!" -ForegroundColor Red
    }
    
    # عد القرارات
    $approved = (Select-String -Path $digest -Pattern "^- " -Context 0 | Where-Object { $_.Line -match "^\- " }).Count
    Write-Host "📝 قرارات موثقة: ~$approved" -ForegroundColor Cyan
}

# 3. فحص transcript
$brainDir = "C:\Users\momen\.gemini\antigravity-ide\brain"
if (Test-Path $brainDir) {
    $latestSession = Get-ChildItem $brainDir -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestSession) {
        $transcript = Join-Path $latestSession.FullName ".system_generated\logs\transcript.jsonl"
        if (Test-Path $transcript) {
            $turns = (Get-Content $transcript).Count
            if ($turns -lt 50) {
                Write-Host "`n📜 Transcript: $turns جولة ✅" -ForegroundColor Green
            } else {
                Write-Host "`n📜 Transcript: $turns جولة ⚠️ يحتاج تنظيف!" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
