# ZX Compressors repository migration plan

Prepared 2026-10-14 from ZX-video `93e93664087cbde415f922fab2957eac9f1096bc`.
The user requests a plan for a separate compressor repository consumed by
ZX-video through Git subtree. Implementation starts with a fresh source
checkpoint so intervening library changes are included.

## Repository and integration decisions

Create one repository named `zx-compressors`, displayed as **ZX Compressors**,
with independent ZX0 and raw LZSA2 packages. Proposed owner: `Witali`, matching
ZX-video's current origin. Resolve visibility and any existing repository with
that name at implementation kickoff. Preserve Python imports `zx0` and `lzsa`,
distribution names `zxvideo-zx0` and `zxvideo-lzsa`, CLI entry points and their
current 0.1.0 package versions for the structural migration.

Import the new repository at ZX-video's existing `libraries/` prefix. Its
root therefore contains `zx0/` and `lzsa/`; `toolkit/codec_libraries.py` can
keep resolving `libraries/<package>/src`. Other projects can install either
package or generate an assembly include for their own RAM layout.

Use full-history subtree integration, consistently without `--squash`, for
initial registration and subsequent imports. Establish the existing prefix
with `split --rejoin`; preserve the same split options in future exports.
This follows Git's extraction/rejoin workflow. Its filtered history retains
library changes, while original ZX-video commit IDs remain provenance in the
historical reports. [Git subtree reference](https://github.com/git/git/blob/master/contrib/subtree/git-subtree.adoc).

## Target layout and ownership

```text
zx-compressors/
  zx0/                    independently installable package and examples
  lzsa/                   independently installable package and examples
  tests/                  portable host, native and export regressions
  evidence/               immutable historical component reports
  README.md
  CHANGELOG.md
  PROVENANCE.json
  .gitattributes
  .gitignore
  .github/workflows/      standalone package and native verification

ZX-video/
  libraries/              Git subtree of the repository above
  toolkit/codec_integration/
                          application-specific benchmark and producer checks
  zx-compressors.lock.json
                          reviewed upstream commit and integration metadata
  ZX_COMPRESSORS_PLAN.md   this integration plan
```

| Content | Maintained in |
| --- | --- |
| Host codec APIs, Z80 generators, relocation, exports and package examples | ZX Compressors |
| Generic native harnesses, seeded valid streams, short-word/overlap/EOF/IRQ checks | ZX Compressors |
| Existing optional profiles and retained unsuccessful component experiments | ZX Compressors, with historical provenance |
| Movie-derived fixtures, their complete timing comparisons and producer checks | ZX-video |
| Video transforms, packet structure, AY, paging/disk supply and publication schedule | ZX-video |
| Application instructions, movie releases, disks and large media archives | ZX-video |

Each package keeps its own upstream notices and license. Preserve original
assembly resources and their byte hashes. Carry `libraries/.gitattributes`,
per-package attributes and ignore rules into the exported root; verify their
coverage for all six upstream assembly resources. Add `/.worktree/` before
creating the first task worktree in the new repository. Document repository
rules and provenance in English.

## Compatibility checkpoint

Capture the current main commit, all tracked files under `libraries/`, emitted
regions/labels, producer outputs and the commands/environment used to verify
them. Save hashes before reorganizing tests or documentation.

The retained reference is the codec merge `f145ca4f`: 18 library tests and
67 toolkit tests passed, protecting 31 default decoder profiles, four original
resources and both producer variants. The later planning snapshot includes
other main changes. Recheck the selected implementation checkpoint; historical
test counts are reference coverage, not a new test result.

Keep the wire formats, default options, emitted bytes/addresses/labels,
register and stack contracts, EOF behavior, overlap and streaming semantics.
All optional coroutine and resident profiles remain available, including
Small's documented CPU/stack tradeoff. A structural move has a deterministic
instruction delta of 0 T when emitted code is identical. Record absolute
retained counts and that difference using the existing timing metadata.

Keep `verification.json`, the two optimization summaries, input hashes,
saved reports and failed experiments intact. New provenance records the
original ZX-video source commit/path and the filtered export commit. Existing
baseline IDs refer to ZX-video, not to rewritten subtree history; repair
documentation links with original repository permalinks instead of rewriting
historical measurements.

## Milestones

### 1 Freeze and classify the source

Create the implementation worktree on its own `codex/` branch under
`<ZX-video-root>/.worktree/<task-name>`. Verify Git subtree availability,
clean tracked state and the latest main before choosing the export checkpoint.
Record repository creation settings and preserve unrelated working files.

Classify every script in `libraries/tests` by its inputs and imports. Current
couplings that need explicit treatment include:

- `measure_long_copy.py`: source/fixture helpers plus real data under
  `toolkit/row_lzsa_evidence`.
- `measure_bit_phases.py`: the toolkit token shim and real ZX0 archives under
  `toolkit/inplace_zx0_evidence`.
- `compare_producer.py`: toolkit producer modules and `git show` of an original
  ZX-video revision.
- `measure_ring_table.py` and `measure_tricks.py`: source paths calculated
  from the enclosing ZX-video tree.
- `test_libraries.py`: imports helpers from benchmark scripts, including
  noncanonical streams and the Mega builder, even for portable unit cases.
- Summary scripts: authenticate shared reports and include application test
  observations; distinguish offline authentication from application replay.

**Exit:** a file/test ownership map, source hashes and a fresh passing baseline.
Every old test has an assigned portable or application destination.

### 2 Export the library history

From the frozen migration branch, create a filtered export branch:

```powershell
git subtree split --prefix=libraries --branch codex/zx-compressors-export
```

Compare the export root tree with the source commit's `libraries` tree. They
must match before bootstrap edits. Record both commit IDs and the split options.
Inspect the exported paths/history for application assets or credentials.
Prepare a separate checkout from that export branch; retain its commit ancestry.

**Exit:** an exact filtered tree with library history and a provenance manifest.
ZX-video's checked-in prefix remains in place.

### 3 Make the exported repository self contained

Extract portable fixture generators from the benchmark modules so unit tests
import no toolkit module at collection time. Use package APIs such as
`zx0.block.build('mega')` in portable tests instead of the movie benchmark
builder. Keep separate package source paths and the same native emulator pin.

Prepare ZX-video counterparts of application scripts under
`toolkit/codec_integration/` before removing their old subtree paths. Preserve
their full real-block coverage and independent producer checks. Give the
integration runners explicit fixture/source paths; remove parent-directory
assumptions from standalone runners. Update reproduction commands and links.

Keep generators unchanged while refactoring test paths. Add standalone CI for
the supported Python minimum/reference versions on Windows and Linux, with
native execution enabled in a designated job. Build and independently install
both wheels outside the source tree; check imports, original resources, CLI
exports and reconstructed ORG/DB bytes. Use deterministic synthetic fixtures
for standalone coverage. Real-movie performance replay remains in ZX-video.

Preserve the historical report files byte for byte. Populate a component
changelog with the original dated codec entries from ZX-video's root changelog,
including unsuccessful attempts, original scope and repository references.
Add English component rules in AGENTS.md and the new migration results.
Record the final standalone coverage without dropping unsuccessful experiments.

**Exit:** independent package installs and a standalone suite work without a
ZX-video checkout, movie assets, OpenCV or AY/TR-DOS application modules.

### 4 Create and publish ZX Compressors

After the standalone result is reviewable, create the selected GitHub target
as an empty repository, with the resolved owner/visibility. If a target already
exists, inspect it and preserve its work before choosing an import approach.
Push the filtered history plus focused bootstrap commits as `main`.

Create an immutable initial release/tag after CI passes. A `v0.1.0` repository
tag is suitable if available and matching the unchanged package versions.
Publish wheels and reproducible assembly examples with profile/address
metadata and licenses. Record the upstream commit hashes; each later package
release advances its version when its distribution changes.

**Exit:** a fresh clone of the new repository builds/tests both packages and
the recorded tag/commit identifies the reviewed result.

### 5 Register the existing prefix and import the release

Recheck that `libraries/` on the migration branch still matches the export
checkpoint. If it changed, incorporate those changes and repeat the affected
standalone/integration gates. Register its filtered ancestry in place:

```powershell
git subtree split --prefix=libraries --rejoin
```

Confirm the resulting split is the recorded export commit and that this join
changed no working-tree files. Fetch the new remote and import the reviewed
full commit, rather than a moving branch tip:

```powershell
git remote add zx-compressors git@github.com:Witali/zx-compressors.git
git fetch zx-compressors --tags
git subtree merge --prefix=libraries <reviewed-full-commit>
```

The URL is the proposed target and must match the resolved repository settings.
Use the existing remote when already configured correctly. Because `libraries`
already exists, initial registration uses rejoin rather than `subtree add`.
Do not remove/re-add the prefix to manufacture an empty directory.

Keep `toolkit/codec_libraries.py` and compatibility imports working at their
current paths. Complete the separately prepared integration runner relocation.
Put the dependency record outside the subtree in `zx-compressors.lock.json`:
remote URL, prefix, reviewed upstream SHA/tag, export source SHA and full-history
policy. The imported commit already pins the Git contents; the record makes
the selected version explicit for review and CI without a self-reference in
the child repository.

**Exit:** the prefix tree equals the reviewed upstream root tree, subtree
ancestry is recorded, application tests run and a normal clone obtains the
library files without submodule initialization.

### 6 Verify and merge the integration

Run the portable suite and all retained application codec tests on merged main.
Compare the 31 default byte/address/label profiles, all six resource hashes,
both producer variants, optional profile outputs and generated assembly
metadata to the checkpoint. Reproduce real LZSA2/ZX0 block comparisons with
the same input hashes and CPU measurement endpoints; demand an exact timing
match for the unchanged generators. Verify guarded input waits/frontiers,
short word escapes, overlap, EOF, relocation and register-preserving IRQs.
Retained integration scopes include 95 full LZSA2 cases, 417 resident ZX0
cases, 64 banked ZX0 blocks and both 42-case/six-placement guarded modes.
Map each runner and fixture to these recorded scopes before moving it.

Check a clean ZX-video clone and an independent compressor clone, package
installs and application build entry points. Record test coverage rather than
claiming the old count if tests were reorganized. Existing TRDs/media must be
byte-identical. Changes to player instructions, ABI or generated bytes leave
the structural-migration scope and require their own timing and application
qualification before promotion.

Update the root changelog/task brief with the target SHA and results, commit
each complete change separately, then merge/push the migration branch after
the implementation's required checks pass.

**Exit:** reproducible standalone and ZX-video verification, unchanged codec
behavior/default performance and a published subtree integration.

## Ongoing updates

Develop reusable codec fixes in ZX Compressors first. Run its suite, publish
a reviewed commit/release, fetch it in ZX-video, merge that specific commit
under `libraries/`, update the dependency record and run application gates.
Keep application configuration and release data outside the subtree.

For a fix discovered inside ZX-video, commit library files separately from
application files, then export to an upstream topic branch for review:

```powershell
git subtree push --prefix=libraries zx-compressors codex/codec-fix
```

Merge the reviewed fix in ZX Compressors and import the resulting upstream
commit into ZX-video. Avoid force pushes and direct exports to upstream `main`.
Maintain the same full-history/split policy. This keeps one canonical source
while retaining practical local fixes in project worktrees.

Other projects may install a pinned revision from the two package directories
using pip's `#subdirectory=zx0` or `#subdirectory=lzsa` syntax, or use a released
wheel. A Python build stage can export the chosen Z80 decoder with explicit
code/state/stack addresses; assembly-only consumers can include the prepared
artifact and its metadata. [pip VCS reference](https://pip.pypa.io/en/stable/topics/vcs-support/).

## Completion and rollback

The migration is complete when both repositories pass their respective suites,
the imported tree/version record agree, all default/resource/producer hashes
and identical-input T-state comparisons match, and ordinary cloning/building
requires no project-specific bootstrap for the libraries. Keep the complete
old-to-new test/reproduction map and original report provenance.

Retain the pre-migration main SHA, export branch/SHA and reviewed upstream tag.
Before publication, abandon or repair the isolated migration branch without
changing main. After a published merge, use a reviewed revert/new corrective
commit that restores the prior library tree, runners and dependency record;
do not rewrite shared history or delete the new repository. Verify the restored
checkpoint. If subtree registration is reverted, repeat ancestry registration
explicitly before a later import.

Repository creation, source extraction, implementation and publication are
future milestones. This request's deliverable is the saved plan.
