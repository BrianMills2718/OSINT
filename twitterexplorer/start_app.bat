@echo off
echo TwitterExplorer Advanced Investigation System
echo =============================================

echo Validating environment...
cd twitterexplorer
python verify_app.py

if %errorlevel% == 0 (
    echo.
    echo Starting TwitterExplorer...
    echo Opening in your browser at http://localhost:8501
    echo Use Ctrl+C to stop the server
    echo.
    python -m streamlit run streamlit_app_modern.py
) else (
    echo.
    echo Environment validation failed. Please check the errors above.
    pause
)