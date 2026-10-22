Set-Location $PSScriptRoot\..\..\..
.venv\Scripts\flask --app wsgi db upgrade
.venv\Scripts\flask --app wsgi seed-demo
