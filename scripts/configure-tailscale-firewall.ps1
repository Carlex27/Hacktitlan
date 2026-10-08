param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.(\d{1,3})\.(\d{1,3})$')]
    [string]$TailscaleIPv4,
    [int]$Port = 8765
)

# Run elevated. Restricts the API to the configured Tailscale address and CGNAT peers.
$ErrorActionPreference = "Stop"
$ruleName = "Hacktitlan API - Tailscale only"
Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress $TailscaleIPv4 -LocalPort $Port -RemoteAddress "100.64.0.0/10"
Write-Host "Regla aplicada a ${TailscaleIPv4}:${Port}. Configure HACKTITLAN_API_HOST con esa IP."
