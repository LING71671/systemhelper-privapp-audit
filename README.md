# com.mobiletools.systemhelper 行为分析

记录一台 Xiaomi Redmi（Android 16）上预置组件的权限、采集内容、网络行为和关闭方法。

## 结论

该组件用于运营商终端自注册和网络质量采集，安装在系统特权目录。代码中的采集内容包括设备标识、双卡信息、
小区、经纬度，以及逐应用的前台使用时长和流量；上报数据经过加密，支持通过 HTTP POST 发送。

2026-11-04 读取手机状态：上报同意开关为 `0`，后台运行限制为 `ignore`，进程未运行。
14:25:02 至 14:25:22（UTC+8），UID `10101` 的上、下行统计均未增加。
本轮未修改设置或手动触发注册服务，未确认实际上报服务器，也未读取应用私有目录。

## 检查结果

| 检查项 | 结果 | 依据 |
|---|---|---|
| 安装在系统特权目录 | 是 | `/system/priv-app/SystemHelper/SystemHelper.apk` |
| 默认授予危险权限 | 是 | 5 个危险权限带 `GRANTED_BY_DEFAULT`，含后台定位 |
| 开机启动 | 已声明 | 监听 `BOOT_COMPLETED`，priority 为 `2147483647`；采样时进程未运行 |
| 电池优化白名单 | 未发现 | `dumpsys deviceidle whitelist` 无此包 |
| 读取 IMEI / IMSI / ICCID | 代码中存在 | 上报 JSON 含 `IMEI1/2 IMSI1/2 ICCID1/2` |
| 采集经纬度 | 代码中存在 | 接入百度定位 SDK，读取经纬度、海拔、速度和方位 |
| 采集应用使用情况 | 代码中存在 | 前台时长和逐 UID 流量，区分 SIM1、SIM2、WiFi |
| 本地缓存门牌级地址 | 未证实 | 已识别的上报字段无地址文本；私有目录未读取 |
| 上传 WiFi 名称 | 未证实 | 自有上报 JSON 无 SSID 字段；百度 SDK 存在读取调用 |
| 本轮流量 | 20 秒内无增量 | `UID stats` 累计上行 138,942 B、857 个包，下行 510,307 B、808 个包 |

## 关闭方法

连接 adb 后执行以下命令，无需 root：

```bash
adb shell settings put secure operator_service_improve_plan 0
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
```

第一条关闭上报同意开关，第二条设置后台运行限制。
验证和恢复命令见 [处置方法](docs/mitigation.md)；需要 AI 助手执行时，见 [操作提示词](docs/guide-with-ai.md)。

## 文档

| 文件 | 内容 |
|---|---|
| [docs/guide-with-ai.md](docs/guide-with-ai.md) | 连接准备、操作提示词和验证标准 |
| [docs/analysis.md](docs/analysis.md) | 组件、权限、采集字段、加密通道、定时机制 |
| [docs/measurements.md](docs/measurements.md) | 本轮采集的设置、CPU、流量、闹钟和访问限制 |
| [docs/mitigation.md](docs/mitigation.md) | 关闭、观测和恢复命令 |
| [docs/reproduce.md](docs/reproduce.md) | 样本提取、静态分析脚本和运行期取证命令 |

## 目录

```
scripts/
  axml.py        二进制 AndroidManifest.xml 解析
  dex_strings.py DEX 字符串表提取
  dex_scan.py    逐方法扫描调用/字符串/字段引用
  dump_method.py 单方法反汇编（取常量实值）
```

四个脚本只依赖 Python 标准库，不需要 JDK、jadx 或 apktool。

## 适用范围

- 样本为一个通用运营商定制组件，不同机型/地区固件里的版本、字段、服务器地址可能不同。
- 代码分析说明组件具备哪些行为，不代表每次运行都执行了这些行为。
- 实测来自单台设备，流量统计不能用于推算长期上传频率或完整历史。

## 声明

分析对象为本人持有设备上的预置应用，目的为隐私自查与安全评估。文中不含样本文件本体。
设备序列号、SIM 标识、WiFi 名称、内网地址、本机路径均已脱敏。
