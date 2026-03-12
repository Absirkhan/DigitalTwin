# Add Redis to Windows PATH
# Run this as Administrator

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Add Redis to System PATH" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Run this script again" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}

$redisPath = "C:\Program Files\Redis"

# Check if Redis exists
if (-not (Test-Path $redisPath)) {
    Write-Host "❌ Redis not found at $redisPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Redis first." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Redis found at: $redisPath" -ForegroundColor Green
Write-Host ""

# Get current system PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

# Check if Redis is already in PATH
if ($currentPath -like "*$redisPath*") {
    Write-Host "✅ Redis is already in system PATH!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You may need to restart your terminal for changes to take effect." -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 0
}

# Add Redis to PATH
Write-Host "📝 Adding Redis to system PATH..." -ForegroundColor Cyan

try {
    $newPath = $currentPath + ";" + $redisPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")

    Write-Host "✅ Redis added to system PATH successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "  ✅ PATH Updated Successfully!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: You must restart your terminal for changes to take effect!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After restarting your terminal, test Redis:" -ForegroundColor Cyan
    Write-Host "  redis-cli ping" -ForegroundColor White
    Write-Host ""
    Write-Host "Expected output: PONG" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host "❌ Error adding to PATH: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can add manually:" -ForegroundColor Yellow
    Write-Host "  1. Open System Properties > Environment Variables" -ForegroundColor White
    Write-Host "  2. Edit 'Path' in System variables" -ForegroundColor White
    Write-Host "  3. Add: C:\Program Files\Redis" -ForegroundColor White
    Write-Host ""
}

pause
