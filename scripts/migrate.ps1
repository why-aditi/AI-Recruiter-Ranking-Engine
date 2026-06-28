$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location "$Root\backend"
& "$Root\.venv\Scripts\python.exe" -m alembic upgrade head
