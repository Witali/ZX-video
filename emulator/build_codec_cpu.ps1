[CmdletBinding()]
param([string]$VcVars,[string]$OutputDirectory,[string[]]$ExtraSources=@())
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory=Join-Path $repo '.tmp/codec-cpu' }
if (-not $VcVars) {
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $installation=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $installation) { throw 'Visual Studio C++ Build Tools were not found.' }
    $VcVars=Join-Path $installation 'VC/Auxiliary/Build/vcvars64.bat'
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$output=[System.IO.Path]::GetFullPath($OutputDirectory)
$sources=@((Join-Path $PSScriptRoot 'src/codec_cpu.c'))
$spectrum=Join-Path $PSScriptRoot 'src/spectrum128.c'
if (Test-Path -LiteralPath $spectrum) { $sources+=@($spectrum) }
$sources=@($sources+$ExtraSources | ForEach-Object { [System.IO.Path]::GetFullPath($_) } | Select-Object -Unique)
$quoted=($sources | ForEach-Object { '"'+[System.IO.Path]::GetFullPath($_)+'"' }) -join ' '
$command='"'+$VcVars+'" >nul && cl /nologo /std:c11 /O2 /MT /LD /TC '+$quoted+' /Fo"'+$output+'/" /Fe"'+$output+'/codec_cpu.dll" /link /IMPLIB:"'+$output+'/codec_cpu.lib" /INCREMENTAL:NO'
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) { throw 'CPU library build failed.' }
$sha=[System.Security.Cryptography.SHA256]::Create()
try {
    $inputs=[ordered]@{}
    $paths=@($sources)+@((Join-Path $PSScriptRoot 'src/codec_cpu.h'),$PSCommandPath)
    $spectrumHeader=Join-Path $PSScriptRoot 'src/spectrum128.h'
    if (Test-Path -LiteralPath $spectrumHeader) { $paths+=@($spectrumHeader) }
    $paths+=@(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'vendor/z80_tester') -File | ForEach-Object { $_.FullName })
    $paths+=@(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'tools') -File | ForEach-Object { $_.FullName })
    foreach ($path in $paths) {
        $text=[System.IO.File]::ReadAllText($path).Replace("`r`n","`n")
        $bytes=[System.Text.Encoding]::UTF8.GetBytes($text)
        $key=[System.IO.Path]::GetRelativePath($repo,$path).Replace('\','/')
        $inputs[$key]=([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
    }
    $dll=Join-Path $output 'codec_cpu.dll'
    $manifest=[ordered]@{abi_version=2;created_utc=[DateTime]::UtcNow.ToString('o');
        flags=@('/std:c11','/O2','/MT','/LD','/TC','/INCREMENTAL:NO');
        source_sha256_lf=$inputs;dll_sha256=(Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()}
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'build.json') -Encoding utf8
} finally { $sha.Dispose() }
Write-Output (Join-Path $output 'codec_cpu.dll')
