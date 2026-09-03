# The actual interactive logic behind "Run Weekly Tracker (Windows).bat".
#
# Written in PowerShell rather than batch, on purpose: batch has no
# reliable native way to check whether "20260230" is a real calendar
# date (Feb 30 doesn't exist) short of shelling out to something else
# anyway, and PowerShell's own [datetime]::ParseExact already does this
# correctly and predictably. Keeping ALL the interactive logic in one
# well-defined language (instead of splitting it between batch's many
# quoting/expansion edge cases and an embedded PowerShell one-liner)
# is easier to get right the first time, especially for changes made
# without a real Windows machine to test on directly.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Read-ValidDate {
    param(
        [string]$Prompt,
        [bool]$RejectFuture = $false
    )
    while ($true) {
        $raw = (Read-Host $Prompt) -replace "-", ""
        $parsed = $null
        $ok = [datetime]::TryParseExact(
            $raw, "yyyyMMdd", [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::None, [ref]$parsed
        )
        if (-not $ok) {
            Write-Host "That's not a valid date. Enter it as YYYYMMDD, e.g. 20260804."
            continue
        }
        if ($RejectFuture -and $parsed.Date -gt (Get-Date).Date) {
            Write-Host "That end date is in the future. Enter a date up to today."
            continue
        }
        return $raw
    }
}

Write-Host "=========================================="
Write-Host " US-China Relations Tracker"
Write-Host "=========================================="
Write-Host ""
Write-Host "What would you like to run?"
Write-Host "  1) Last complete week (just press Enter for this)"
Write-Host "  2) A specific date range instead"
Write-Host ""
$choice = Read-Host "Enter 1 or 2"
Write-Host ""

if ($choice -eq "2") {
    Write-Host "Enter dates as YYYYMMDD, e.g. 20260804."
    Write-Host ""
    # Read-Host appends its own ": " to whatever prompt text it's given,
    # so the prompt here is just "Start date"/"End date" with no colon
    # of our own — passing "Start date: " would have displayed a
    # doubled "Start date: : ".
    $startDate = Read-ValidDate -Prompt "Start date"
    $endDate = Read-ValidDate -Prompt "End date" -RejectFuture $true
    Write-Host ""
    & "$PSScriptRoot\run_week.bat" --start $startDate --end $endDate
} else {
    & "$PSScriptRoot\run_week.bat"
}

Write-Host ""
# Read-Host (waits for Enter), not $Host.UI.RawUI.ReadKey (waits for any
# single key) — RawUI.ReadKey can throw in some PowerShell hosts (the
# ISE, certain restricted/redirected consoles) where raw key input isn't
# available; Read-Host works reliably everywhere a normal console does,
# at the small cost of needing Enter specifically rather than any key.
Read-Host "Press Enter to close this window" | Out-Null
