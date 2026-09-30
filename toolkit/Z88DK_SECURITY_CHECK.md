# z88dk download and antivirus check

Checked on 2026-09-30. **The Windows binary archive remains quarantined.**
The source archive and locally built Linux tools produced no new Defender
detections in the two completed custom scans. This is a bounded antivirus
check, not a proof that either distribution is free of malware.

## Origin and quarantine

- Official project: [z88dk/z88dk](https://github.com/z88dk/z88dk), linked
  from [z88dk.org](https://z88dk.org/site/).
- Windows download: [z88dk-win32-2.4.zip, release v2.4](https://github.com/z88dk/z88dk/releases/tag/v2.4),
  117797132 bytes. GitHub's release API publishes SHA-256
  `26d9880ee2e43077808ac86a4b6247a81f5dadc30563ca7cedc58bc4fb5ccb57`.
  The local file could not be hashed after Defender blocked it; this is
  the publisher's digest, not a verified local digest.
- At 17:17:13 local time (UTC+02:00), Defender detected
  `Trojan:Win32/Qwexlafiba!rfn`, threat ID 2147965225, in that archive.
  Event 1117 confirms successful **quarantine at 17:17:35**, error zero.
  The failed 7-Zip extraction reports zero extracted files. No executable
  from that Windows archive was run.
- No quarantine restore, allow action, antivirus exception or protection
  disablement was performed. The detection is not classified as a false
  positive by this assessment. An [older upstream issue about v2.3](https://github.com/z88dk/z88dk/issues/2474)
  concerns a different archive and is not evidence that this one is safe.

## Completed checks

Run [scan_z88dk.ps1](scan_z88dk.ps1) from the repository root. The script
updates signatures, scans the source archive and source build directory,
and correlates scan-start event 1000 with completion event 1001 by scan ID.
The saved [JSON evidence](z88dk_security_check.json) removes user identities.

| Target under `.tmp/z80-c-compilers` | Completed (UTC+02:00) | Result |
| --- | --- | --- |
| `z88dk-src-2.4.tgz` | 17:31:57 | No new detection; completion event confirmed |
| `z88dk-source` including built Linux tools | 17:33:02 | No new detection; completion event confirmed |

Defender and real-time protection were enabled; archive scanning was enabled.
Signatures updated from 1.459.484.0 to **1.459.485.0** before the scans.
No new detection/remediation events occurred during these scans. The one
z88dk detection retained in history is the earlier quarantined Windows ZIP.

The 55296853-byte [official source archive](https://github.com/z88dk/z88dk/releases/download/v2.4/z88dk-src-2.4.tgz)
has local SHA-256
`96a57a01d44ff1d65d84e38b04aebb0a4e10eccb4845cb71f5a26f10abe7c5ac`,
matching the GitHub release API's digest. Linux binaries were compiled
locally in the existing Ubuntu/WSL environment, not taken from the flagged ZIP.

## Limits and decision

- Defender's exclusion list was not visible to this process: its command
  returned "Must be an administrator to view exclusions". The scans completed,
  but this assessment cannot certify that no pre-existing exclusion affected
  coverage. No exclusion was added or changed.
- The release build also fetched `zsdcc_r15248_src.tar.gz` from the project's
  `http://nightly.z88dk.org/zsdcc/` service. Its observed SHA-256 is
  `2e78ae85defb6c984c7f4a74a1d5821c7fa507220a721d693d5ceb9e3b967da7`.
  This dependency and its extracted tree were inside the scanned directory.
  An HTTPS verification attempt failed with `SSL: WRONG_VERSION_NUMBER`.
  This observed hash is a reproducibility pin, not independent authentication
  of the initial HTTP transfer.
- A public VirusTotal hash-report lookup was inaccessible; no multi-engine
  verdict was obtained and no local files were uploaded.
- This was not a full system scan, source security audit, or independent
  review of the release build system. A negative scan does not establish
  that the quarantined archive was a false positive.

Keep the Windows ZIP quarantined. Continue the component experiment using
the scanned source-built Linux tools; retain the above supply-chain limits.

## Requested multi-engine upload attempt

The user subsequently authorized uploading the compiled executable to a
multi-engine web scanner. The compiler actually built and run here is the
Linux/WSL ELF executable `z88dk-zsdcc`, not a Windows PE `.exe`:

- Local file: `.tmp/z80-c-compilers/z88dk-source/z88dk/bin/z88dk-zsdcc`
- Size: 25538352 bytes
- SHA-256: `e7b325206d3cd5b4da53b45282748cacec7d2cefe6485f25145ce9efaf2735cf`
- Destination attempted: [VirusTotal upload](https://www.virustotal.com/gui/home/upload)

The site opened, but all three supported file-chooser attempts timed out
(accessibility button, Playwright button and direct file-input attempt).
The file selection/upload did not complete; **no file was submitted and
no multi-engine verdict was obtained**. This is an interrupted verification,
not a clean result. The Windows archive was not restored or uploaded.

Manual continuation: open the upload page, choose the above local file,
complete submission, then verify the report's SHA-256 matches this record.
Keep any verdict for the Linux compiler separate from the quarantined
Windows ZIP, which is a different artifact.
