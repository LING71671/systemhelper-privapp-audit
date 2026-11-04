"""Dump a single DEX method's instructions with resolved operands."""
import struct
import sys

sys.path.insert(0, "scripts")
from dex_scan import Dex, W, uleb  # noqa: E402

NAMES = {
    0x00: "nop", 0x01: "move", 0x02: "move/from16", 0x03: "move/16",
    0x04: "move-wide", 0x05: "move-wide/from16", 0x06: "move-wide/16",
    0x07: "move-object", 0x08: "move-object/from16", 0x09: "move-object/16",
    0x0A: "move-result", 0x0B: "move-result-wide", 0x0C: "move-result-object",
    0x0D: "move-exception", 0x0E: "return-void", 0x0F: "return",
    0x10: "return-wide", 0x11: "return-object", 0x12: "const/4", 0x13: "const/16",
    0x14: "const", 0x15: "const/high16", 0x16: "const-wide/16", 0x17: "const-wide/32",
    0x18: "const-wide", 0x19: "const-wide/high16", 0x1A: "const-string",
    0x1B: "const-string/jumbo", 0x1C: "const-class", 0x1D: "monitor-enter",
    0x1E: "monitor-exit", 0x1F: "check-cast", 0x20: "instance-of",
    0x21: "array-length", 0x22: "new-instance", 0x23: "new-array",
    0x24: "filled-new-array", 0x25: "filled-new-array/range", 0x26: "fill-array-data",
    0x27: "throw", 0x28: "goto", 0x29: "goto/16", 0x2A: "goto/32",
    0x2B: "packed-switch", 0x2C: "sparse-switch", 0x27 + 1: "cmp",
    0x6E: "invoke-virtual", 0x6F: "invoke-super", 0x70: "invoke-direct",
    0x71: "invoke-static", 0x72: "invoke-interface", 0x74: "invoke-virtual/range",
    0x75: "invoke-super/range", 0x76: "invoke-direct/range",
    0x77: "invoke-static/range", 0x78: "invoke-interface/range",
}


def dump(dex, midx, code_off):
    b = dex.buf
    _r, _i, _o, _t, _dbg, n = struct.unpack_from("<HHHHII", b, code_off)
    base = code_off + 16
    print("### %s  (insns=%d)" % (dex.method(midx), n))
    i = 0
    while i < n:
        u = struct.unpack_from("<H", b, base + i * 2)[0]
        op = u & 0xFF
        name = NAMES.get(op, "op_%02x" % op)
        extra = ""
        if op == 0x12:  # const/4
            v = (u >> 12) & 0xF
            extra = "v%d, #%d" % ((u >> 8) & 0xF, v - 16 if v >= 8 else v)
        elif op in (0x13, 0x15, 0x16):  # const/16, const/high16, const-wide/16
            v = struct.unpack_from("<h", b, base + (i + 1) * 2)[0]
            if op == 0x15:
                extra = "v%d, #%d" % ((u >> 8) & 0xFF, v << 16)
            else:
                extra = "v%d, #%d" % ((u >> 8) & 0xFF, v)
        elif op in (0x14, 0x17):  # const, const-wide/32
            v = struct.unpack_from("<i", b, base + (i + 1) * 2)[0]
            extra = "v%d, #%d" % ((u >> 8) & 0xFF, v)
        elif op == 0x18:
            lo, hi = struct.unpack_from("<ii", b, base + (i + 1) * 2)
            extra = "v%d, #%d" % ((u >> 8) & 0xFF, (hi << 32) | (lo & 0xFFFFFFFF))
        elif op == 0x1A:
            extra = '"%s"' % dex.string(struct.unpack_from("<H", b, base + (i + 1) * 2)[0])
        elif op == 0x1B:
            extra = '"%s"' % dex.string(struct.unpack_from("<I", b, base + (i + 1) * 2)[0])
        elif 0x6E <= op <= 0x72 or 0x74 <= op <= 0x78:
            extra = dex.method(struct.unpack_from("<H", b, base + (i + 1) * 2)[0])
        elif 0x52 <= op <= 0x6D:
            extra = dex.field(struct.unpack_from("<H", b, base + (i + 1) * 2)[0])
        if u == 0x0100:
            size = struct.unpack_from("<H", b, base + (i + 1) * 2)[0]
            print("%4d  packed-switch-payload size=%d" % (i, size))
            i += size * 2 + 4
            continue
        if u == 0x0200:
            size = struct.unpack_from("<H", b, base + (i + 1) * 2)[0]
            print("%4d  sparse-switch-payload size=%d" % (i, size))
            i += size * 4 + 2
            continue
        if u == 0x0300:
            ew, size = struct.unpack_from("<HI", b, base + (i + 1) * 2)
            print("%4d  array-payload" % i)
            i += (ew * size + 1) // 2 + 4
            continue
        print("%4d  %-24s %s" % (i, name, extra))
        i += W[op]


if __name__ == "__main__":
    dex = Dex(sys.argv[1])
    cls_needle, meth_needle = sys.argv[2], sys.argv[3]
    for cname, cdata in dex.classes():
        if cls_needle not in cname:
            continue
        for midx, off in dex.methods(cdata):
            if meth_needle in dex.method(midx) and off:
                dump(dex, midx, off)
                print()
