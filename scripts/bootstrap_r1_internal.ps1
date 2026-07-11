# Bootstrap R1 internal dev (no customer deliverables required)
param(
    [switch]$SkipIndex,
    [switch]$SkipEval,
    [switch]$SkipSmoke,
    [switch]$ForceSeed,
    [switch]$AllowWarnings
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
Set-Location $Root
$Backend = Join-Path $Root "backend"
$env:PYTHONPATH = $Backend

Write-Host "==> R1 internal bootstrap (no customer data required)"
Initialize-AriaEnv -LocalHostPaths

Write-Host "==> DB migrate..."
& "$Root\scripts\migrate.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Seed internal engagements..."
$seedArgs = @()
if ($ForceSeed) { $seedArgs += "--force" }
python "$Root\scripts\seed_internal_engagement.py" @seedArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipIndex) {
    if ($env:MOCK_RAG -eq "true") {
        Write-Host "==> Skip ingest (MOCK_RAG=true). Set MOCK_RAG=false + start postgres for full index."
    }
    elseif ($env:DATABASE_URL -notmatch "^postgresql") {
        Write-Host "==> Skip ingest (DATABASE_URL is not PostgreSQL)."
    }
    else {
        Write-Host "==> Ingest knowledge_base -> pgvector..."
        python "$Root\scripts\ingest_documents.py"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Ingest failed — ensure postgres + ollama embedding are up."
        }
        elseif (-not $SkipEval) {
            Write-Host "==> Retrieval eval (15 queries, gate 12/15)..."
            python "$Root\scripts\run_r1_retrieval_eval.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Retrieval eval below gate — OK for first bootstrap; re-run after corpus index."
            }
        }
    }
}

if (-not $SkipSmoke) {
    $base = if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://localhost:8000/api/v1" }
    Write-Host "==> Smoke health ($base)..."
    $smokeArgs = @("--base-url", $base, "--health-only")
    if ($AllowWarnings) { $smokeArgs += "--allow-warnings" }
    python "$Root\scripts\r1_e2e_smoke.py" @smokeArgs
}

Write-Host ""
Write-Host "Internal bootstrap done. Next:"
Write-Host "  .\scripts\start-local.ps1          # backend + worker + frontend"
Write-Host "  python scripts\r1_e2e_smoke.py ... # full RFQ flow when stack is up"
Write-Host "  Users:  .\scripts\create_dev_users.ps1   (when AUTH_ENABLED=true)"
Write-Host "  Rehearsal: docs/R1/r1-rehearsal-script.md"
Write-Host "  Customer O-02a/O-03 replace seed data when contract signed."
