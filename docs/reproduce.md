# 复现步骤

## 工具

需要 adb 和 Python 3。仓库中的脚本只依赖 Python 标准库。

| 脚本 | 作用 |
|---|---|
| `axml.py` | 解析二进制 `AndroidManifest.xml`，输出可读 XML |
| `dex_strings.py` | 提取 DEX 字符串表 |
| `dex_scan.py` | 遍历方法，输出方法调用、字符串常量和字段引用 |
| `dump_method.py` | 反汇编单个方法，解析常量、字符串和方法引用 |
| `verify_gates.py` | 提取厂商判断、变量写入和编码静态默认值 |

## 静态分析

以下命令在仓库根目录执行，样本路径以 `pm path` 的实际返回值为准：

```bash
# 1. 提取样本
adb shell pm path com.mobiletools.systemhelper
adb pull /system/priv-app/SystemHelper/SystemHelper.apk .

# 2. 解包
python -c "import zipfile;zipfile.ZipFile('SystemHelper.apk').extractall('unpack')"

# 3. 解析清单
python scripts/axml.py unpack/AndroidManifest.xml > manifest.xml

# 4. 提取字符串表
python scripts/dex_strings.py unpack/classes.dex strings.txt

# 5. 扫描全部方法
python scripts/dex_scan.py unpack/classes.dex "" > scan_all.txt

# 6. 扫描业务包
python scripts/dex_scan.py unpack/classes.dex "com/mobiletools" > scan_own.txt

# 7. 读取配置类静态初始化方法
python scripts/dump_method.py unpack/classes.dex "Lc/d/a/b/d;" "<clinit>"

# 8. 核对厂商判断与默认服务器地址
python scripts/verify_gates.py unpack/classes.dex > gate-verification.json
```

第 7 步的类名对应本次样本，其他版本需重新定位。方法调用和字符串引用用于定位行为，
具体执行条件还需核对分支、参数和数据流。

## 运行期取证

```bash
# 版本、UID 和权限授予状态
adb shell dumpsys package com.mobiletools.systemhelper

# 当前进程
adb shell pidof com.mobiletools.systemhelper

# Doze 白名单
adb shell dumpsys deviceidle whitelist

# 已排定的闹钟
adb shell dumpsys alarm

# 网络流量
adb shell dumpsys netstats --poll
adb shell dumpsys netstats detail

# CPU 时间和进程启动次数
adb shell dumpsys batterystats com.mobiletools.systemhelper

# 上报同意开关
adb shell settings get secure operator_service_improve_plan

# 后台运行限制
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

本机 `--poll` 返回 `Forced poll` 后再读取统计。流量使用 `UID stats` 中目标 UID 的全部时间桶汇总，不叠加 `UID tag stats`。
CPU 和启动次数取目标进程的数据，不汇总其他应用。

## 数据脱敏

发布前移除设备序列号、IMSI / ICCID 实际值、WiFi 名称和 BSSID、内网 IP、本机路径及 API Key。
文档保留包名、版本、文件哈希、权限名、字段名和汇总统计；不附 APK 或应用私有数据。
