"""Targeted DEX scanner: per-method invoked methods + string constants.

Enough to reconstruct behaviour without a full decompiler:
  - which framework APIs each own method calls
  - which string literals flow into them
"""
import struct
import sys

W = [1] * 0x100
for op in [0x02, 0x05, 0x08, 0x13, 0x15, 0x16, 0x19, 0x1A, 0x1C, 0x1F, 0x20, 0x22, 0x23, 0x29]:
    W[op] = 2
for op in list(range(0x2D, 0x3E)) + list(range(0x44, 0x6E)) + list(range(0x90, 0xB0)) + list(range(0xD0, 0xE3)):
    W[op] = 2
for op in [0x03, 0x06, 0x09, 0x14, 0x17, 0x1B, 0x24, 0x25, 0x26, 0x2A, 0x2B, 0x2C]:
    W[op] = 3
for op in list(range(0x6E, 0x73)) + list(range(0x74, 0x79)):
    W[op] = 3
W[0x18] = 5


def uleb(buf, off):
    r = s = 0
    while True:
        b = buf[off]
        off += 1
        r |= (b & 0x7F) << s
        if not b & 0x80:
            return r, off
        s += 7


class Dex:
    def __init__(self, path):
        self.buf = open(path, "rb").read()
        b = self.buf
        self.string_ids_size, self.string_ids_off = struct.unpack_from("<II", b, 0x38)
        self.type_ids_off = struct.unpack_from("<I", b, 0x44)[0]
        self.proto_ids_off = struct.unpack_from("<I", b, 0x4C)[0]
        self.field_ids_off = struct.unpack_from("<I", b, 0x54)[0]
        self.method_ids_off = struct.unpack_from("<I", b, 0x5C)[0]
        self.class_defs_size, self.class_defs_off = struct.unpack_from("<II", b, 0x60)
        self._s, self._t = {}, {}

    def string(self, i):
        if i not in self._s:
            off = struct.unpack_from("<I", self.buf, self.string_ids_off + i * 4)[0]
            _, p = uleb(self.buf, off)
            self._s[i] = self.buf[p:self.buf.index(b"\x00", p)].decode("utf-8", "replace")
        return self._s[i]

    def type(self, i):
        if i not in self._t:
            idx = struct.unpack_from("<I", self.buf, self.type_ids_off + i * 4)[0]
            self._t[i] = self.string(idx)
        return self._t[i]

    def proto(self, i):
        _sh, ret, params_off = struct.unpack_from("<III", self.buf, self.proto_ids_off + i * 12)
        params = []
        if params_off:
            n = struct.unpack_from("<I", self.buf, params_off)[0]
            for k in range(n):
                params.append(self.type(struct.unpack_from("<H", self.buf, params_off + 4 + k * 2)[0]))
        return "(%s)%s" % ("".join(params), self.type(ret))

    def method(self, i):
        cls, proto, name = struct.unpack_from("<HHI", self.buf, self.method_ids_off + i * 8)
        return "%s->%s%s" % (self.type(cls), self.string(name), self.proto(proto))

    def field(self, i):
        cls, typ, name = struct.unpack_from("<HHI", self.buf, self.field_ids_off + i * 8)
        return "%s->%s:%s" % (self.type(cls), self.string(name), self.type(typ))

    def classes(self):
        for k in range(self.class_defs_size):
            base = self.class_defs_off + k * 32
            v = struct.unpack_from("<IIIIIIII", self.buf, base)
            yield self.type(v[0]), v[6]

    def methods(self, cdata_off):
        if not cdata_off:
            return
        p = cdata_off
        sf, p = uleb(self.buf, p)
        inf, p = uleb(self.buf, p)
        dm, p = uleb(self.buf, p)
        vm, p = uleb(self.buf, p)
        for _ in range(sf + inf):
            _, p = uleb(self.buf, p)
            _, p = uleb(self.buf, p)
        for count in (dm, vm):
            idx = 0
            for _ in range(count):
                diff, p = uleb(self.buf, p)
                _, p = uleb(self.buf, p)
                code_off, p = uleb(self.buf, p)
                idx += diff
                yield idx, code_off

    def scan_method(self, code_off):
        b = self.buf
        _r, _i, _o, _t, _dbg, insns_size = struct.unpack_from("<HHHHII", b, code_off)
        base = code_off + 16
        strings, calls, fields = [], [], []
        i = 0
        while i < insns_size:
            u = struct.unpack_from("<H", b, base + i * 2)[0]
            op = u & 0xFF
            if u == 0x0100:
                size = struct.unpack_from("<H", b, base + (i + 1) * 2)[0]
                i += size * 2 + 4
                continue
            if u == 0x0200:
                size = struct.unpack_from("<H", b, base + (i + 1) * 2)[0]
                i += size * 4 + 2
                continue
            if u == 0x0300:
                ew, size = struct.unpack_from("<HI", b, base + (i + 1) * 2)
                i += (ew * size + 1) // 2 + 4
                continue
            if op == 0x1A:
                strings.append(self.string(struct.unpack_from("<H", b, base + (i + 1) * 2)[0]))
            elif op == 0x1B:
                strings.append(self.string(struct.unpack_from("<I", b, base + (i + 1) * 2)[0]))
            elif 0x6E <= op <= 0x72 or 0x74 <= op <= 0x78:
                calls.append(self.method(struct.unpack_from("<H", b, base + (i + 1) * 2)[0]))
            elif 0x52 <= op <= 0x6D:
                fields.append(self.field(struct.unpack_from("<H", b, base + (i + 1) * 2)[0]))
            i += W[op]
        return strings, calls, fields


def main():
    dex = Dex(sys.argv[1])
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    for cname, cdata in dex.classes():
        if needle and needle not in cname:
            continue
        print("\n===== %s =====" % cname)
        for midx, code_off in dex.methods(cdata):
            name = dex.method(midx)
            if not code_off:
                print("  [abstract] %s" % name)
                continue
            try:
                ss, cc, ff = dex.scan_method(code_off)
            except Exception as e:  # noqa: BLE001
                print("  [err] %s : %s" % (name, e))
                continue
            print("  %s" % name)
            if ss:
                uniq = sorted({s for s in ss if s.strip()})
                if uniq:
                    print("     str: %s" % " | ".join(uniq))
            if cc:
                print("     call: %s" % ", ".join(cc))
            if ff:
                print("     fld: %s" % ", ".join(ff))


if __name__ == "__main__":
    main()
