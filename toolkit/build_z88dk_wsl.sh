#!/usr/bin/env bash
# Run from the repository root in Ubuntu/WSL after prepare_z80_c_compilers.py
# --z88dk-source. Dependencies: gcc g++ make bison flex libboost-graph-dev
# libboost-regex-dev libgmp-dev libxml2-dev m4 texinfo dos2unix re2c curl.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tools="$root/.tmp/z80-c-compilers"
echo '96a57a01d44ff1d65d84e38b04aebb0a4e10eccb4845cb71f5a26f10abe7c5ac  '"$tools/z88dk-src-2.4.tgz" | sha256sum -c -
mkdir -p "$tools/z88dk-source"
if [ ! -f "$tools/z88dk-source/z88dk/build.sh" ]; then
    tar -xzf "$tools/z88dk-src-2.4.tgz" -C "$tools/z88dk-source"
fi
cd "$tools/z88dk-source/z88dk"
# The release's BUILD_SDCC_HTTP recipe uses this upstream source archive.
# Verify it before allowing the build recipe to extract or compile it.
if [ ! -f zsdcc_r15248_src.tar.gz ]; then
    curl --fail --location http://nightly.z88dk.org/zsdcc/zsdcc_r15248_src.tar.gz -o zsdcc_r15248_src.tar.gz
fi
echo '2e78ae85defb6c984c7f4a74a1d5821c7fa507220a721d693d5ceb9e3b967da7  zsdcc_r15248_src.tar.gz' | sha256sum -c -
BUILD_SDCC=1 BUILD_SDCC_HTTP=1 MAKEFLAGS=-j4 ./build.sh -l -z > "$tools/z88dk-source-build.log" 2>&1
bin/z88dk-zsdcc --version
