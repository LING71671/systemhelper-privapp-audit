"""Inspect consent gates and encoded static defaults without running the APK."""

import hashlib
import json
import struct
import sys

from dex_scan import Dex, W, uleb


TARGETS = {
    "Lc/d/a/a/a;->b(Landroid/content/Context;)Z",
    "Lc/d/a/a/l;->d(Landroid/content/Context;)Z",
    "Lc/d/a/a/l;->a(Landroid/content/Context;Lcom/mobiletools/systemhelper/control/b;)V",
    "Lcom/mobiletools/systemhelper/control/GetSignalInfoReceiver;->b(Landroid/content/Context;)Z",
    "Lc/d/a/b/l;->a(Landroid/content/Context;)Z",
    "Lc/d/a/b/l;->h(Landroid/content/Context;)Ljava/lang/String;",
    "Lcom/mobiletools/systemhelper/control/g;->a(Lcom/mobiletools/systemhelper/control/b;)Z",
    "Lcom/mobiletools/systemhelper/control/e;->a(Lorg/json/JSONObject;)Z",
}

READERS = {
    "Liantong": "b", "nubia": "c", "OPPO": "d", "OnePlus": "e",
    "PTAC": "f", "realme": "g", "samsung": "h", "TDTECH": "i",
    "vivo": "j", "WIKO": "k", "Xiaomi": "l", "ZTE": "m",
}
TARGETS.update(
    "Lc/d/a/a/" + name + ";->a(Landroid/content/Context;Lcom/mobiletools/systemhelper/control/b;)V"
    for name in READERS.values()
)
TARGETS.update({
    "Lc/d/a/a/d;->d(Landroid/content/Context;)Z",
    "Lc/d/a/a/h;->d(Landroid/content/Context;)Z",
    "Lc/d/a/a/j;->d(Landroid/content/Context;)Z",
})


def static_defaults(dex, class_name):
    for index in range(dex.class_defs_size):
        record = struct.unpack_from("<8I", dex.buf, dex.class_defs_off + index * 32)
        if dex.type(record[0]) != class_name:
            continue
        count, offset = uleb(dex.buf, record[6])
        for _ in range(3):
            _, offset = uleb(dex.buf, offset)
        fields = []
        field_index = 0
        for _ in range(count):
            diff, offset = uleb(dex.buf, offset)
            _, offset = uleb(dex.buf, offset)
            field_index += diff
            fields.append(dex.field(field_index))
        if not record[7]:
            return {}
        value_count, offset = uleb(dex.buf, record[7])
        values = {}
        for field in fields[:value_count]:
            header = dex.buf[offset]
            offset += 1
            value_type, value_arg = header & 31, header >> 5
            if value_type == 0x1E:
                value = None
            elif value_type == 0x1F:
                value = bool(value_arg)
            elif value_type in (0x1C, 0x1D):
                raise ValueError("Nested static values are outside this verifier's scope")
            else:
                length = value_arg + 1
                value = int.from_bytes(dex.buf[offset:offset + length], "little")
                offset += length
                if value_type == 0x17:
                    value = dex.string(value)
            values[field] = value
        return values
    raise ValueError("Expected configuration class was not found")


def field_writes(dex, code_offset):
    count = struct.unpack_from("<I", dex.buf, code_offset + 12)[0]
    base = code_offset + 16
    index = 0
    writes = []
    while index < count:
        word = struct.unpack_from("<H", dex.buf, base + index * 2)[0]
        opcode = word & 255
        if word == 0x0100:
            size = struct.unpack_from("<H", dex.buf, base + (index + 1) * 2)[0]
            index += size * 2 + 4
            continue
        if word == 0x0200:
            size = struct.unpack_from("<H", dex.buf, base + (index + 1) * 2)[0]
            index += size * 4 + 2
            continue
        if word == 0x0300:
            width, size = struct.unpack_from("<HI", dex.buf, base + (index + 1) * 2)
            index += (width * size + 1) // 2 + 4
            continue
        if 0x67 <= opcode <= 0x6D:
            field = struct.unpack_from("<H", dex.buf, base + (index + 1) * 2)[0]
            writes.append({"codeUnit": index, "field": dex.field(field)})
        index += W[opcode]
    return writes


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/verify_gates.py <classes.dex>")
    dex = Dex(sys.argv[1])
    methods = []
    for class_name, class_data in dex.classes():
        if not class_name.startswith(("Lc/d/", "Lcom/mobiletools/")):
            continue
        for method_index, code_offset in dex.methods(class_data):
            name = dex.method(method_index)
            if name not in TARGETS or not code_offset:
                continue
            strings, calls, fields = dex.scan_method(code_offset)
            methods.append({
                "method": name,
                "strings": list(dict.fromkeys(strings)),
                "settingsCalls": [call for call in calls if "Landroid/provider/Settings$" in call],
                "readerGateCalls": [call for call in calls if call.startswith("Lc/d/a/a/") and call.endswith("(Landroid/content/Context;)Z")],
                "gateFieldReferences": [field for field in fields if field == "Lc/d/a/b/d;->e:Z"],
                "staticFieldWrites": field_writes(dex, code_offset),
            })
    missing = TARGETS - {method["method"] for method in methods}
    if missing:
        raise SystemExit("Sample differs; expected methods are missing: " + ", ".join(sorted(missing)))
    defaults = static_defaults(dex, "Lc/d/a/b/d;")
    print(json.dumps({
        "dexSha256": hashlib.sha256(dex.buf).hexdigest(),
        "defaultServerAddress": defaults.get("Lc/d/a/b/d;->l:Ljava/lang/String;"),
        "readerClasses": {brand: "Lc/d/a/a/" + name + ";" for brand, name in READERS.items()},
        "methods": methods,
        "scope": "Static bytecode inspection only; does not execute collectors or prove runtime traffic behavior.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
