# Clears the demo IP's logs so you start each presentation run clean.
#   .\clear_demo_ip.ps1              # clears 66.42.25.3
#   .\clear_demo_ip.ps1 1.2.3.4      # clears a different IP
# Runs the backend venv's Python on clear_demo_ip.py (path-independent).
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\clear_demo_ip.py" @args
