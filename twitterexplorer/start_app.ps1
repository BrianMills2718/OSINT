# TwitterExplorer PowerShell Launcher
Write-Host "TwitterExplorer Advanced Investigation System" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Validating environment..." -ForegroundColor Yellow
Set-Location twitterexplorer
python verify_app.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Starting TwitterExplorer..." -ForegroundColor Green
    Write-Host "Opening in your browser at http://localhost:8501" -ForegroundColor Green
    Write-Host "Use Ctrl+C to stop the server" -ForegroundColor Green
    Write-Host ""
    python -m streamlit run streamlit_app_modern.py
} else {
    Write-Host ""
    Write-Host "Environment validation failed. Please check the errors above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}