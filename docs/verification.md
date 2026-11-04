[简体中文](verification_zh.md)

# Verification of reporting controls

Date: 2026-11-04, UTC+8. Target: `com.mobiletools.systemhelper` on one Xiaomi Redmi running Android 16.
Evidence comes from the APK pulled during this session, its original DEX, jadx output, and device observations.

## Finding

The app had no running process and no new traffic during three minutes of observation. The OS rejected a normal background-service start.
In the code, however, the Xiaomi branch checks whether device setup is complete. It does not read `operator_service_improve_plan`.
Its idle state during this test was not caused by this key being checked in the Xiaomi reader.

The network-control page showed SIM 1, SIM 2 and WLAN enabled. These controls were left unchanged.

## Sample

| Item | Value |
|---|---|
| versionName / versionCode | `3.0.1-20250311` / `31` |
| APK SHA256 | `5267008ede808c467988df588915791d21a6f1f3fbe219c57b125a235000df4f` |
| DEX SHA256 | `f6bee7fba7a94241b1f4b1e41f866dd04292d7e909cce387cf8b0044f79c4fba` |
| Current user / UID | `0` / `10101` |
| Manufacturer / Android | `Xiaomi` / `16` |

## Gate assignment

The registration thread `com.mobiletools.systemhelper.control.g` and history thread `control.e` check
`Lc/d/a/b/d;->e:Z`. Logs call it `isUserPermissionOpen`. Its assignment depends on the manufacturer.

The Xiaomi reader `Lc/d/a/a/l;->a(Context, DeviceInfo)` calls `d(Context)` and writes its result to that field.
The getter reads only `Settings.Global.device_provisioned` and compares it with `1`.
Original DEX inspection confirms no `Settings.Secure` read in this getter and a field write at code unit 7 in the reader.
With provisioning complete, this path can set the gate to true even when the consent setting is 0.

## Manufacturer branches in the identical APK

| Branch | Gate source | Effect of consent set to 0 |
|---|---|---|
| vivo | `a/j.d(Context)`: provisioning complete and consent equals 1 | Sets this gate to false; no vivo-device test performed |
| Xiaomi | `a/l.d(Context)`: provisioning only | Does not block this path |
| OPPO, samsung | `a/d.d(Context)`, `a/h.d(Context)`: provisioning only | Does not block this path |
| Liantong, nubia, OnePlus, PTAC, realme, TDTECH, WIKO, ZTE | Base reader `a/a.b(Context)`, provisioning only on the non-vivo path | Does not block this path |

The base reader separately handles vivo. Manufacturer selection is populated from system properties by `a/n.c()`.
The table compares all 12 branches in the identical APK. Device tests were performed only on this Xiaomi phone.

## Device checks

| Check | Result | Supported conclusion |
|---|---|---|
| Consent setting | `0` | The stored setting is off; the Xiaomi reader does not use it |
| Background AppOp | `RUN_ANY_IN_BACKGROUND: ignore` | The restriction is configured |
| Normal service start | Exit 255; `app is in background uid null` | That background start was rejected |
| Foreground-service request | Exit 255; `Not found; no service started.` | Start failed; its specific cause was not established |
| 180-second observation | Seven samples; unchanged byte/packet counters; no app or `:remote` process observed | No counter increase for this UID during the window |

Each network read followed a confirmed `Forced poll`. Totals include all matching `UID stats` buckets and exclude duplicate `UID tag stats`.
Settings were kept unchanged. Both service-start attempts failed, so a complete registration flow was not triggered.

## Helper service and default address

`RegisterHelperService` exposes Binder configuration for the server, intervals and logging.
Its `onCreate` initializes telephony listeners and it does not override `onStartCommand`.
Starting that helper alone is not proof of an active registration attempt.

`http://dm.wo.com.cn:18080/register` is the encoded static initial value of configuration field `a/b/d.l`.
`a/b/l.h(Context)` uses it when the preference is absent. Method string-instruction scans miss encoded static defaults.
The private preference remains inaccessible, so the effective address on the device is unconfirmed.

## Reproduction

```bash
python scripts/verify_gates.py unpack/classes.dex > gate-verification.json
```

The script reports setting calls, reader-gate calls, field writes and encoded defaults.
jadx reported four errors; critical small methods were separately checked against original DEX.
An `app_process` probe for the original gate getters exited with code 137 and produced no result.
This session covered code inspection, service-start attempts and three minutes of traffic observation. No decrypted capture or reboot test was performed.

## Sanitized evidence

The [structured record](evidence/verification-2026-11-04.json) contains hashes, method names, aggregate counters, exit codes and setting states.
It excludes device serials, actual IMEI/IMSI/ICCID, SSID/BSSID, IP addresses, accounts, chat text, local paths and API key values.
The APK, complete decompilation and unfiltered device output are not committed.
