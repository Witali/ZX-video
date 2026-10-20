# Adapted locally from z80-tester d45d8889; no external checkout required.
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Output)
$ErrorActionPreference = 'Stop'
$header = Join-Path (Split-Path -Parent $PSScriptRoot) 'vendor/z80_tester/z80.h'
$expected = '6CA70FFD91B1BDBAF00F7A41E7092B326145FD1C95DCDD7BB01183370DE734F3'
$text = [System.IO.File]::ReadAllText($header)
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text.Replace("`r`n", "`n"))
    $actual = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
} finally { $sha.Dispose() }
if ($actual -ne $expected) {
    throw 'The native model hooks require the pinned, unmodified z80.h. Review hooks before changing the core.'
}
$cases = [regex]::Matches($text, '(?m)^\s*case\s+(\d+):\s*([^\r\n]*?)\s*//\s*(.*?)\s+\((\d+)\)\s*$')
if ($cases.Count -ne 1685) { throw "Expected 1685 numbered decoder states, got $($cases.Count)." }
$table = New-Object byte[] 1685
$seen = @{}
$names = @{}
foreach ($case in $cases) {
    $index = [int]$case.Groups[1].Value
    $name = $case.Groups[3].Value
    if ($index -ge $table.Length -or $seen.ContainsKey($index)) { throw "Unexpected decoder state: $index" }
    $seen[$index] = $true
    $names[$index] = $name
    if ($name -match '^(cb|cbhl|ddfdcb)$') {
        $table[$index] = 2 # CB rotation/BIT writes F; RES/SET preserves F.
    } elseif ($name -match '^(ADD|ADC|SUB|SBC|AND|XOR|OR|CP) ' -or
        $name -match '^(INC|DEC) (B|C|D|E|H|L|A|\(HL\))$' -or
        $name -match '^(NEG|CPL|DAA|RLCA|RRCA|RLA|RRA|SCF|CCF|RRD|RLD)$' -or
        $name -match '^IN (B,\(C\)|C,\(C\)|D,\(C\)|E,\(C\)|H,\(C\)|L,\(C\)|A,\(C\)|\(C\))$' -or
        $name -match '^LD A,(I|R)$' -or
        $name -match '^(LDI|LDD|LDIR|LDDR|CPI|CPD|CPIR|CPDR|INI|IND|INIR|INDR|OUTI|OUTD|OTIR|OTDR)$') {
        $table[$index] = 1
    } elseif ($name -notmatch '^(NOP|ED NOP|HALT|DJNZ |JR |JP |CALL |RET( |$)|RETN$|RETI$|RST |LD |INC (BC|DE|HL|SP)$|DEC (BC|DE|HL|SP)$|EX |EXX$|POP |PUSH |OUT |IN A,\(n\)$|IM |DI$|EI$|(CB|DD|ED|FD) prefix$|int_im[012]$|nmi$)') {
        throw "Unclassified decoder mnemonic at ${index}: $name"
    }
}
$anchors = @{ 55 = 'SCF'; 63 = 'CCF'; 1282 = 'LD A,I'; 1311 = 'LD A,R'; 1392 = 'OUT (C),0'; 221 = 'DD prefix'; 253 = 'FD prefix' }
$repeatAnchors = @{ 1515 = 'LDIR'; 1528 = 'CPIR'; 1541 = 'INIR'; 1554 = 'OTIR'; 1567 = 'LDDR'; 1580 = 'CPDR'; 1593 = 'INDR'; 1606 = 'OTDR' }
foreach ($index in $repeatAnchors.Keys) {
    $anchors[$index] = $repeatAnchors[$index]
    $body = @($cases | Where-Object { [int]$_.Groups[1].Value -eq $index })[0].Groups[2].Value
    if ($body -notmatch 'cpu->wz=--cpu->pc;--cpu->pc;') { throw "Repeat PC hook changed at $index." }
}
foreach ($index in $anchors.Keys) {
    if ($names[$index] -ne $anchors[$index]) { throw "Native hook anchor changed at $index." }
}
$lines = New-Object 'System.Collections.Generic.List[string]'
$lines.Add('/* Generated from pinned z80.h; 0=preserve F, 1=write F, 2=CB opcode dependent. */')
$lines.Add('static const uint8_t q_flags[1685] = {')
for ($offset = 0; $offset -lt $table.Length; $offset += 32) {
    $end = [Math]::Min($offset + 31, $table.Length - 1)
    $lines.Add(('    ' + ($table[$offset..$end] -join ',') + ','))
}
$lines.Add('};')
[System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($Output), (($lines -join "`n")+"`n"), [System.Text.UTF8Encoding]::new($false))
