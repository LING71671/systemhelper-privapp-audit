# com.mobiletools.systemhelper 行为分析

记录一台 Xiaomi Redmi（Android 16）上预置组件的权限、采集内容、网络行为和后台限制方法。

## 结论

该组件用于运营商终端自注册和网络质量采集，安装在系统特权目录。代码中的采集内容包括设备标识、双卡信息、
小区、经纬度，以及逐应用的前台使用时长和流量；上报数据经过加密，支持通过 HTTP POST 发送。

手机上看，进程没有运行，连续 3 分钟也没有新增流量。普通后台服务启动时，系统返回 `app is in background`。

但看代码，小米分支检查的是「开机向导是否完成」，并没有读取 `operator_service_improve_plan`。
所以，这次看起来停了，并不是代码响应了这个开关。只有 vivo 分支额外检查它。

实测时间为 2026-11-04 14:52:46 至 14:55:46（UTC+8），后台限制保持为 `ignore`。

完整依据见 [深度核对报告](docs/verification_zh.md)。

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
| 同意开关能否关闭本机业务逻辑 | 不能 | 小米分支使用 `device_provisioned`，未检查该同意开关 |
| 普通后台服务启动 | 被拒绝 | `Error: app is in background uid null` |
| 本轮流量 | 180 秒内无增量 | 强制刷新后，`UID stats` 累计上行 138,942 B、857 个包，下行 510,307 B、808 个包 |

## 后台限制

连接 adb 后执行以下命令，无需 root：

```bash
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

预期返回 `ignore`。
手机端联网入口、验证范围和恢复命令见 [处置方法](docs/mitigation.md)；
需要 AI 助手执行时，见 [操作提示词](docs/guide-with-ai.md)。

## 文档

| 文件 | 内容 |
|---|---|
| [docs/guide-with-ai.md](docs/guide-with-ai.md) | 连接准备、操作提示词和验证标准 |
| [docs/analysis.md](docs/analysis.md) | 组件、权限、采集字段、加密通道、定时机制 |
| [docs/measurements.md](docs/measurements.md) | 本轮采集的设置、CPU、流量、闹钟和访问限制 |
| [docs/mitigation.md](docs/mitigation.md) | 后台限制、系统联网入口、观测和恢复命令 |
| [docs/reproduce.md](docs/reproduce.md) | 样本提取、静态分析脚本和运行期取证命令 |
| [docs/verification_zh.md](docs/verification_zh.md) | 厂商分支、关闭效果与脱敏证据；[English](docs/verification.md) |

## 目录

```
scripts/
  axml.py        二进制 AndroidManifest.xml 解析
  dex_strings.py DEX 字符串表提取
  dex_scan.py    逐方法扫描调用/字符串/字段引用
  dump_method.py 单方法反汇编（取常量实值）
  verify_gates.py 核对厂商判断与 DEX 静态默认值
```

这些脚本只依赖 Python 标准库，不需要 JDK、jadx 或 apktool。
