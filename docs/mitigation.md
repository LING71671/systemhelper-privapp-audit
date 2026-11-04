# 处置方法

前提：adb 已连接，手机已允许 USB 调试。以下操作无需 root。
需要 AI 助手执行时，见 [操作提示词](guide-with-ai.md)。

## 1. 确认应用和原设置

```bash
adb shell pm path com.mobiletools.systemhelper
adb shell dumpsys package com.mobiletools.systemhelper
adb shell settings get secure operator_service_improve_plan
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

记录应用版本、当前用户的 UID 和两项设置的原值。本机主用户 UID 为 `10101`，其他设备需重新确认。

## 2. 关闭上报同意开关

代码在发送前检查「运营商服务改进计划」开关，值为 `0` 时跳过发送。

```bash
adb shell settings put secure operator_service_improve_plan 0
adb shell settings get secure operator_service_improve_plan
```

预期返回 `0`。本轮读取时已为 `0`，未重复修改。

## 3. 设置后台运行限制

```bash
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
```

预期包含 `ignore`。本轮读取时已为 `ignore`，未重复修改。
该值表示后台限制已配置，不代表所有启动方式或已排定的闹钟都被禁用。本机仍有该应用的闹钟记录。

## 4. 观测流量

间隔 20 秒读取两次：

```bash
adb shell dumpsys netstats detail
```

在 `UID stats` 中汇总目标 UID 全部时间桶的 `rb`（下行字节）和 `tb`（上行字节），比较两次差值。
不叠加 `UID tag stats`，也不只取 `uid=` 后的第一条记录。

本轮 20 秒内上、下行统计均未增加，未手动启动注册服务。详细数据见 [运行期实测](measurements.md)。

## 5. 恢复

恢复操作前记录的值。若原值分别为 `allow` 和 `1`：

```bash
adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND allow
adb shell settings put secure operator_service_improve_plan 1
```

若原设置不存在或 AppOp 使用默认值，应恢复对应的原状态，不直接套用上述值。

## 6. 验证范围

本轮只读取了应用、系统设置和运行统计，未测试卸载、停用或权限撤回，也未逐项验证通话、支付和系统更新。
系统升级后可重新读取两项设置，确认是否保留。
