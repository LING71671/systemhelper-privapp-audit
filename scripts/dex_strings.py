"""DEX string table extractor (no external deps)."""
import struct
import sys


def uleb128(buf, off):
    result = 0
    shift = 0
    while True:
        b = buf[off]
        off += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, off
        shift += 7


def dex_strings(path):
    buf = open(path, "rb").read()
    if buf[:4] != b"dex\n":
        raise ValueError("not a dex: %r" % buf[:4])
    string_ids_size, string_ids_off = struct.unpack_from("<II", buf, 0x38)
    out = []
    for i in range(string_ids_size):
        (data_off,) = struct.unpack_from("<I", buf, string_ids_off + i * 4)
        if data_off == 0:
            continue
        _, p = uleb128(buf, data_off)
        end = buf.index(b"\x00", p)
        raw = buf[p:end]
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("utf-8", "replace")
        out.append(s)
    return out


if __name__ == "__main__":
    ss = dex_strings(sys.argv[1])
    print("count", len(ss))
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        for s in ss:
            f.write(s.replace("\n", "\\n") + "\n")
