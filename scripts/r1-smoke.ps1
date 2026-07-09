param(
    [string]$BaseUrl = "http://localhost/api/v1",
    [string]$Username = "",
    [string]$Password = "",
    [switch]$HealthOnly,
    [switch]$AllowWarnings
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Smoke = Join-Path $Root "r1_e2e_smoke.py"
$Rfq = Join-Path (Split-Path -Parent $Root) "samples\rfq\mock_chassis_rfq.docx"

$argsList = @("--base-url", $BaseUrl, "--rfq", $Rfq)
if ($HealthOnly) { $argsList += "--health-only" }
if ($AllowWarnings) { $argsList += "--allow-warnings" }
if ($Username) { $argsList += @("--username", $Username) }
if ($Password) { $argsList += @("--password", $Password) }

python $Smoke @argsList
exit $LASTEXITCODE
