# Run in an elevated PowerShell on the server. StartWhenAvailable covers a missed 02:00 run.
$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "run-backup.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Hacktitlan-DailyBackup" -Action $action -Trigger $trigger -Settings $settings -Description "Respaldo verificado diario de Hacktitlan" -Force
