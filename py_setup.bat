@echo off
setlocal

:: Define Python version and installation directory
set PYTHON_VERSION=3.10.0
set PYTHON_DIR=%~dp0python_embed

:: Check if Python is already installed in the specified directory
if exist "%PYTHON_DIR%\python.exe" (
    echo Python is already installed in %PYTHON_DIR%.
    goto :install_packages
)

:: Download Python embeddable zip package
echo Downloading Python %PYTHON_VERSION% embeddable package...
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip -OutFile python_embed.zip"

:: Extract the Python embeddable package
echo Extracting Python...
powershell -Command "Expand-Archive -Path python_embed.zip -DestinationPath \"%PYTHON_DIR%\""
if %ERRORLEVEL% NEQ 0 (
    echo Python installation failed...
    del python_embed.zip
    exit /b 1
)

:: Clean up the downloaded zip file
del python_embed.zip

:: Add Python to PATH for this session
set PATH=%PYTHON_DIR%;%PATH%
echo Python has been installed locally in %PYTHON_DIR%.

echo Change python_embed\python%PYTHON_VERSION%._pth and uncomment "import site"
pause

:install_packages
:: Check for requirements.txt
IF NOT EXIST "requirements.txt" (
    echo requirements.txt not found. Please make sure it is in the same directory as this script.
    exit /b 1
)

:: Install pip (since it's not included in the embeddable package)
echo Installing pip...
powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py"
"%PYTHON_DIR%\python.exe" get-pip.py
if %ERRORLEVEL% NEQ 0 (
    echo Pip installation failed. Attempting to reinstall...
    "%PYTHON_DIR%\python.exe" get-pip.py
)
if %ERRORLEVEL% NEQ 0 (
    echo Pip installation failed again. Please check your internet connection or install pip manually.
    del get-pip.py
    exit /b 1
)

del get-pip.py

:: Install required packages from requirements.txt
echo Installing required Python packages...
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip
"%PYTHON_DIR%\python.exe" -m pip install -r requirements.txt

echo Setup complete. You can now run Python scripts using %PYTHON_DIR%\python.exe.

endlocal
