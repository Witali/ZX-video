"""Build unmodified Speex 1.2.1 for controlled PC tests with MSVC.

No installed compiler settings or system files are changed. Both libraries
are host tools, not Z80 binaries. Download/extract the official source first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


SOURCES = '''cb_search exc_10_32_table exc_8_128_table filters gain_table
hexc_table high_lsp_tables lsp ltp speex stereo vbr vq bits exc_10_16_table
exc_20_32_table exc_5_256_table exc_5_64_table gain_table_lbr hexc_10_32_table
lpc lsp_tables_nb modes modes_wb nb_celp quant_lsp sb_celp speex_callbacks
speex_header window'''.split()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--vcvars', type=Path, required=True)
    args = p.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    # Only a trusted, explicit local batch path enters cmd.exe; reject shell
    # metacharacters rather than claiming JSON string escaping is shell quoting.
    batch = str(args.vcvars.resolve())
    if any(c in batch for c in '"&|<>^%!\r\n'):
        raise ValueError('unsupported shell characters in vcvars path')
    env_text = subprocess.run(f'cmd.exe /d /s /c ""{batch}" >nul && set"',
                              capture_output=True, text=True, check=True).stdout
    env = {k.upper():v for k, v in os.environ.items()}
    for line in env_text.splitlines():
        if '=' in line and not line.startswith('='):
            key, value = line.split('=', 1)
            env[key.upper()] = value
    compiler = shutil.which('cl.exe', path=env['PATH'])
    if not compiler:
        raise RuntimeError('vcvars did not provide cl.exe')
    env['VSLANG'] = '1033'
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for variant, define in (('float', 'FLOATING_POINT'), ('fixed', 'FIXED_POINT')):
        folder = out/variant
        folder.mkdir()
        (folder/'config.h').write_text(f'#define {define}\n#define inline __inline\n#define EXPORT\n',
                                     encoding='utf-8', newline='\n')
        command = [compiler, '/nologo', '/O2', '/LD', '/DHAVE_CONFIG_H', '/D_CRT_SECURE_NO_WARNINGS',
                   '/I'+str(folder), '/I'+str(source/'include'), '/I'+str(source/'libspeex')]
        command += [str(source/'libspeex'/(name+'.c')) for name in SOURCES]
        command += ['/link', '/DEF:'+str(source/'win32/libspeex.def'), '/OUT:'+str(folder/'speex.dll')]
        result = subprocess.run(command, env=env, cwd=folder, capture_output=True)
        (folder/'build.log').write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        rows.append(dict(variant=variant, command=command,
                         dll_sha256=hashlib.sha256((folder/'speex.dll').read_bytes()).hexdigest()))
    hashes = {str(f.relative_to(source)):hashlib.sha256(f.read_bytes()).hexdigest()
              for f in source.rglob('*') if f.is_file() and f.suffix in ('.c', '.h', '.def')}
    (out/'build.json').write_text(json.dumps(dict(source_version='1.2.1', rows=rows,
                                                source_file_hashes=hashes), indent=2)+'\n',
                                 encoding='utf-8', newline='\n')
    print(json.dumps([dict(variant=r['variant'], dll_sha256=r['dll_sha256']) for r in rows]))


if __name__ == '__main__':
    main()
