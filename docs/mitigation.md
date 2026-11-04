# 后台限制与联网控制

这份 APK 的小米分支没有读取 `operator_service_improve_plan`。本机目前设置了后台限制，
普通服务启动被系统拒绝。厂商差异见 [深度核对报告](verification_zh.md)。

## 1. 记录原状态

```bash
adb shell pm path com.mobiletools.systemhelper
adb shell dumpsys package com.mobiletools.systemhelper
adb shell settings get global device_provisioned
adb shell settings get secure operator_service_improve_plan
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

记录应用版本、当前用户 UID 和后台限制原值。本机主用户 UID 为 `10101`，其他设备需重新确认。

## 2. 限制后台运行

```bash
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

预期包含 `ignore`。本轮读取时已为该值，未重复修改。
本机普通服务启动返回 `app is in background`。闹钟记录仍然存在。

## 3. 小米系统联网入口

通过应用信息页进入「联网控制 / Network access」；本机可用以下命令打开应用信息：

```bash
adb shell am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.mobiletools.systemhelper
```

本机页面显示 SIM 1、SIM 2、WLAN 都已开启。若系统允许关闭，可按网络类型分别限制，随后重新观测流量。
本轮只查看了页面，尚未测试这些开关。小米的系统说明提到，部分系统应用不受常规控制。
见 [小米系统设置说明](https://trust.mi.com/docs/miui-privacy-white-paper-global/3/1)。

## 4. 观测流量

先刷新，再读取统计；每次采样都执行：

```bash
adb shell dumpsys netstats --poll
adb shell dumpsys netstats detail
```

本机刷新返回 `Forced poll`。汇总 `UID stats` 中目标 UID 全部时间桶的 `rb`、`tb`，不叠加 `UID tag stats`。
本轮连续 180 秒、7 个采样点均无增量。

## 5. 恢复

恢复操作前记录的 AppOp 值。若原值为 `allow`：

```bash
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND allow
```

原值为默认状态时应恢复 `default`。本轮没有修改同意开关或联网控件，无需为本轮检查恢复这些项目。
