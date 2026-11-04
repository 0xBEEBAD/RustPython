"""Read SizeOfStackReserve out of a PE header: the PGO builds must keep the
8 MB main-thread stack that .cargo/config.toml asks for, because RUSTFLAGS
replaces (not extends) the config's rustflags."""
import struct, sys

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        data = f.read(4096)
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    # COFF header is 20 bytes; optional header follows. PE32+ puts
    # SizeOfStackReserve at optional-header offset 72.
    reserve = struct.unpack_from("<Q", data, e_lfanew + 24 + 72)[0]
    print(f"{path}: SizeOfStackReserve = {reserve:#x} ({reserve}) "
          f"{'OK' if reserve == 0x7A1200 else 'WRONG, expected 0x7a1200'}")
