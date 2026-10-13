"""Inspect the deliverable itself; reject partial ABIs and missing offline runtime."""
import hashlib, json, pathlib, struct, sys, zipfile

apk = pathlib.Path(sys.argv[1])
expected = {'arm64-v8a': 183, 'x86_64': 62}
required = {'libappmodules.so', 'libreactnative.so', 'libhermesvm.so',
            'libexpo-modules-core.so', 'libexpo-sqlite.so', 'librnskia.so',
            'libgesturehandler.so', 'libreanimated.so', 'libworklets.so'}
groups = {}
with zipfile.ZipFile(apk) as archive:
    assert archive.read('assets/index.android.bundle')[:8].hex() == 'c61fbc03c103191f', 'Missing Hermes bytecode'
    entries = [n for n in archive.namelist() if n.startswith('lib/') and n.endswith('.so')]
    abis = {n.split('/')[1] for n in entries}
    assert abis == set(expected), f'Unexpected or incomplete ABI set: {abis}'
    for abi, machine in expected.items():
        names = [n for n in entries if n.split('/')[1] == abi]
        assert required <= {n.split('/')[-1] for n in names}, f'Missing runtime libraries for {abi}'
        for name in names:
            data = archive.read(name)
            assert data[:6] == b'\x7fELF\x02\x01', f'Not a 64-bit little-endian ELF: {name}'
            assert struct.unpack_from('<H', data, 18)[0] == machine, name
            phoff = struct.unpack_from('<Q', data, 32)[0]
            size, count = struct.unpack_from('<HH', data, 54)
            align = [struct.unpack_from('<Q', data, phoff+i*size+48)[0]
                     for i in range(count) if struct.unpack_from('<I', data, phoff+i*size)[0] == 1]
            assert align and (abi != 'arm64-v8a' or min(align) >= 16384), f'ARM64 16-KiB alignment: {name}'
        groups[abi] = len(names)
print(json.dumps({'ok': True, 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
                  'sizeBytes': apk.stat().st_size, 'nativeLibraries': groups,
                  'hermes': True, 'arm64Elf16KiBAligned': True}, indent=2))
