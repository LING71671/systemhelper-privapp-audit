"""Minimal AndroidManifest.xml (binary AXML) parser -> readable XML."""
import struct
import sys

RES_XML_TYPE = 0x0003
RES_STRING_POOL_TYPE = 0x0001
RES_XML_START_NAMESPACE_TYPE = 0x0100
RES_XML_END_NAMESPACE_TYPE = 0x0101
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
RES_XML_CDATA_TYPE = 0x0104
RES_XML_RESOURCE_MAP_TYPE = 0x0180

# attribute data types
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
TYPE_REFERENCE = 0x01

ATTR_NAME_IDS = {
    0x0101021B: "versionCode",
    0x0101021C: "versionName",
    0x01010003: "name",
    0x01010000: "theme",
    0x01010001: "label",
    0x01010002: "icon",
}


def parse_string_pool(buf, off):
    typ, hsize, size = struct.unpack_from("<HHI", buf, off)
    str_count, style_count, flags, strings_start, styles_start = struct.unpack_from(
        "<IIIII", buf, off + 8
    )
    is_utf8 = (flags & (1 << 8)) != 0
    offsets = struct.unpack_from("<%dI" % str_count, buf, off + hsize)
    base = off + strings_start
    out = []
    for o in offsets:
        p = base + o
        if is_utf8:
            # utf16 length (varint), then byte length (varint)
            n, p = _varint8(buf, p)
            n2, p = _varint8(buf, p)
            out.append(buf[p:p + n2].decode("utf-8", "replace"))
        else:
            n, p = _varint16(buf, p)
            out.append(buf[p:p + n * 2].decode("utf-16-le", "replace"))
    return out, size


def _varint8(buf, p):
    v = buf[p]
    if v & 0x80:
        return ((v & 0x7F) << 8) | buf[p + 1], p + 2
    return v, p + 1


def _varint16(buf, p):
    (v,) = struct.unpack_from("<H", buf, p)
    if v & 0x8000:
        v2 = struct.unpack_from("<H", buf, p + 2)[0]
        return ((v & 0x7FFF) << 16) | v2, p + 4
    return v, p + 2


def value_to_str(strings, resid, dtype, data):
    if dtype == TYPE_STRING:
        return strings[data] if data < len(strings) else str(data)
    if dtype == TYPE_INT_BOOLEAN:
        return "true" if data != 0 else "false"
    if dtype == TYPE_INT_HEX:
        return "0x%08x" % (data & 0xFFFFFFFF)
    if dtype == TYPE_REFERENCE:
        return "@ref/0x%08x" % (data & 0xFFFFFFFF)
    return str(data)


def parse_axml(path):
    buf = open(path, "rb").read()
    typ, hsize, total = struct.unpack_from("<HHI", buf, 0)
    assert typ == RES_XML_TYPE, hex(typ)
    strings = []
    res_map = []
    out = []
    stack = []
    depth = 0
    off = hsize
    while off < total:
        ctype, chsize, csize = struct.unpack_from("<HHI", buf, off)
        if csize == 0:
            break
        if ctype == RES_STRING_POOL_TYPE:
            strings, _ = parse_string_pool(buf, off)
        elif ctype == RES_XML_RESOURCE_MAP_TYPE:
            n = (csize - chsize) // 4
            res_map = list(struct.unpack_from("<%dI" % n, buf, off + chsize))
        elif ctype == RES_XML_START_ELEMENT_TYPE:
            ns_i, name_i, attr_start, attr_size, attr_count = struct.unpack_from(
                "<IIHHH", buf, off + chsize
            )
            tag = strings[name_i]
            attrs = []
            p = off + chsize + attr_start
            for _ in range(attr_count):
                a_ns, a_name, a_raw, _vsize, _res0, a_type, a_data = struct.unpack_from(
                    "<IIIHBBI", buf, p
                )
                key = strings[a_name] if a_name < len(strings) else str(a_name)
                if a_name < len(res_map):
                    key = ATTR_NAME_IDS.get(res_map[a_name], key)
                val = value_to_str(strings, a_raw, a_type, a_data)
                attrs.append((key, val))
                p += attr_size
            pad = "  " * depth
            aset = " ".join('%s="%s"' % (k, v) for k, v in attrs)
            out.append("%s<%s%s%s>" % (pad, tag, " " if aset else "", aset))
            stack.append(len(out) - 1)
            depth += 1
        elif ctype == RES_XML_END_ELEMENT_TYPE:
            depth -= 1
            pad = "  " * depth
            name_i = struct.unpack_from("<I", buf, off + chsize + 4)[0]
            if stack and stack[-1] == len(out) - 1:
                out[-1] = out[-1][:-1].rstrip() + " />"
            else:
                out.append("%s</%s>" % (pad, strings[name_i]))
            if stack:
                stack.pop()
        elif ctype == RES_XML_CDATA_TYPE:
            d = struct.unpack_from("<I", buf, off + chsize)[0]
            if d < len(strings):
                out.append("  " * depth + strings[d])
        off += csize
    return "\n".join(out)


if __name__ == "__main__":
    print(parse_axml(sys.argv[1]))
