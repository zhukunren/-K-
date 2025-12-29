@echo off                                                                                                                                                          
  setlocal enabledelayedexpansion                                                                                                                                    
                                                                                                                                                                     
  REM Installs frontend dependencies in frontend/ (npm install or npm ci)                                                                                            
  REM Usage: scripts\install_frontend.bat [--ci] [--clean]                                                                                                           
                                                                                                                                                                     
  set "SCRIPT_DIR=%~dp0"                                                                        
  set "REPO_ROOT=%SCRIPT_DIR%"                                                                  
  if exist "%SCRIPT_DIR%..\frontend\package.json" set "REPO_ROOT=%SCRIPT_DIR%.."                
  pushd "%REPO_ROOT%"                                                                                                                                           
                                                                                                                                                                     
  set "FRONTEND_DIR=frontend"                                                                                                                                        
                                                                                                                                                                     
  if not exist "%FRONTEND_DIR%" (                                                                                                                                    
    echo [ERROR] frontend directory not found: "%CD%\%FRONTEND_DIR%"                                                                                                 
    popd                                                                                                                                                             
    exit /b 1                                                                                                                                                        
  )                                                                                                                                                                  
                                                                                                                                                                     
  where npm >nul 2>nul                                                                                                                                               
  if errorlevel 1 (                                                                                                                                                  
    echo [ERROR] npm not found. Install Node.js and ensure npm is on PATH.                                                                                           
    popd                                                                                                                                                             
    exit /b 1                                                                                                                                                        
  )                                                                                                                                                                  
                                                                                                                                                                     
  set "USE_CI=0"                                                                                                                                                     
  set "FORCE_CLEAN=0"                                                                                                                                                
                                                                                                                                                                     
  :parse_args                                                                                                                                                        
  if "%~1"=="" goto args_done                                                                                                                                        
  if /i "%~1"=="--ci" set "USE_CI=1" & shift & goto parse_args                                                                                                       
  if /i "%~1"=="--clean" set "FORCE_CLEAN=1" & shift & goto parse_args                                                                                               
  if /i "%~1"=="-h" goto show_help                                                                                                                                   
  if /i "%~1"=="--help" goto show_help                                                                                                                               
  echo [WARN] Unknown option: %~1                                                                                                                                    
  shift                                                                                                                                                              
  goto parse_args                                                                                                                                                    
                                                                                                                                                                     
  :args_done                                                                                                                                                         
                                                                                                                                                                     
  pushd "%FRONTEND_DIR%"                                                                                                                                             
                                                                                                                                                                     
  if "%FORCE_CLEAN%"=="1" (                                                                                                                                          
    if exist "node_modules" (                                                                                                                                        
      echo Removing node_modules...                                                                                                                                  
      rmdir /s /q "node_modules"                                                                                                                                     
    )                                                                                                                                                                
  )                                                                                                                                                                  
                                                                                                                                                                     
  set "ERR=0"                                                                                                                                                        
                                                                                                                                                                     
  if "%USE_CI%"=="1" (                                                                                                                                               
    if exist "package-lock.json" (                                                                                                                                   
      echo Running npm ci in "%CD%" ...                                                                                                                              
      call npm ci                                                                                                                                                    
      set "ERR=!ERRORLEVEL!"                                                                                                                                         
      goto done                                                                                                                                                      
    )                                                                                                                                                                
  )                                                                                                                                                                  
                                                                                                                                                                     
  echo Running npm install in "%CD%" ...                                                                                                                             
  call npm install                                                                                                                                                   
  set "ERR=!ERRORLEVEL!"                                                                                                                                             
                                                                                                                                                                     
  :done                                                                                                                                                              
  popd                                                                                                                                                               
  popd                                                                                                                                                               
                                                                                                                                                                     
  if not "%ERR%"=="0" (                                                                                                                                              
    echo [ERROR] npm exited with code %ERR%                                                                                                                          
    exit /b %ERR%                                                                                                                                                    
  )                                                                                                                                                                  
  echo Dependencies installed successfully.                                                                                                                          
  exit /b 0                                                                                                                                                          
                                                                                                                                                                     
  :show_help                                                                                                                                                         
  echo Usage: scripts\install_frontend.bat [--ci] [--clean]                                                                                                          
  echo   --ci     Use "npm ci" when package-lock.json exists                                                                                                         
  echo   --clean  Remove node_modules before installing                                                                                                              
  popd                                                                                                                                                               
  exit /b 0