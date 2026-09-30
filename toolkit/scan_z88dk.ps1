# Scan the local z88dk source package and source-built tools with Defender.
# Requires access to Defender commands. Never restores quarantine or changes exclusions.
[CmdletBinding()]
param([string]$Output = '.tmp/z80-c-compilers/z88dk-defender-scan.json', [switch]$CollectOnly)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$scanRoot = Join-Path $repoRoot '.tmp/z80-c-compilers'
$scanTargets = @('z88dk-src-2.4.tgz', 'z88dk-source')
if ($CollectOnly) {
    $previous = Get-Content -LiteralPath (Join-Path $repoRoot $Output) -Raw | ConvertFrom-Json
    $started = [datetime]$previous.started
    $scans = @($previous.scans)
} else {
    $started = Get-Date
    Update-MpSignature -ErrorAction Stop
    $scans = @()
    foreach ($relative in $scanTargets) {
        $path = Join-Path $scanRoot $relative
        if (-not (Test-Path -LiteralPath $path)) { throw "Missing scan target: $relative" }
        Write-Output "Scanning $relative"
        $begin = Get-Date
        Start-MpScan -ScanType CustomScan -ScanPath $path -ErrorAction Stop
        $scans += [ordered]@{ target = $relative; started = $begin.ToString('o'); returned = (Get-Date).ToString('o') }
    }
}
$status = Get-MpComputerStatus
# Event log publication can lag behind Start-MpScan returning.
for ($attempt = 0; $attempt -lt 10; $attempt++) {
  $events = @(Get-WinEvent -FilterHashtable @{
    LogName = 'Microsoft-Windows-Windows Defender/Operational'
    StartTime = $started; Id = @(1000,1001,1002,1005,1116,1117)
} -ErrorAction SilentlyContinue | Sort-Object TimeCreated | ForEach-Object {
    [xml]$xml = $_.ToXml()
    $data = [ordered]@{}
    foreach ($item in $xml.Event.EventData.Data) {
        # Keep neutral event codes and results, without user identities or localized labels.
        if ($item.Name -in @('Product Version','Scan ID','Scan Type Index','Scan Parameters Index',
                'Scan Resources','Scan Time Hours','Scan Time Minutes','Scan Time Seconds',
                'Threat ID','Threat Name','Path','Action ID','Error Code')) {
            $data[$item.Name] = ([string]$item.'#text').Replace($repoRoot, '<repository>')
        }
    }
    [ordered]@{ id = $_.Id; time = $_.TimeCreated.ToString('o'); data = $data }
  })
  $starts = @($events | Where-Object { $_.id -eq 1000 -and $_.data['Scan Resources'] -match 'z88dk' })
  $ends = @($events | Where-Object { $_.id -eq 1001 })
  $completed = @($starts | Where-Object { $_.data['Scan ID'] -in @($ends | ForEach-Object { $_.data['Scan ID'] }) })
  if ($completed.Count -eq $scans.Count) { break }
  Start-Sleep -Seconds 1
}
$detections = @(Get-MpThreatDetection | Where-Object {
    ($_.Resources -join ' ') -match 'z88dk|zsdcc'
} | ForEach-Object {
    [ordered]@{
        threat_id = $_.ThreatID; detected = $_.InitialDetectionTime.ToString('o')
        last_change = $_.LastThreatStatusChangeTime.ToString('o')
        action_success = $_.ActionSuccess; status_id = $_.ThreatStatusID
        resources = @($_.Resources | ForEach-Object { $_.Replace($repoRoot, '<repository>') })
    }
})
$report = [ordered]@{
    started = $started.ToString('o'); finished = (Get-Date).ToString('o')
    antivirus_enabled = $status.AntivirusEnabled
    realtime_enabled = $status.RealTimeProtectionEnabled
    signature_version = $status.AntivirusSignatureVersion
    signatures_updated = $status.AntivirusSignatureLastUpdated.ToString('o')
    completed_scans_confirmed_by_event_id = $completed.Count
    scans = $scans; events = $events; detections = $detections
    limitation = 'A negative scan is not proof of safety. The quarantined Windows binary archive was not restored or rescanned.'
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $repoRoot $Output) -Encoding utf8
Write-Output "Report: $Output"
