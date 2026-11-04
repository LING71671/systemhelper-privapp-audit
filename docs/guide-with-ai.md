# 用 AI 助手执行关闭操作

需要能在电脑上执行命令的 AI 助手，例如 Codex、Claude Code 或 Cursor。

## 1. 连接手机

1. 在「设置 → 我的设备 → 全部参数与信息」中连续点击 OS 版本 7 次，开启开发者模式。
2. 在「设置 → 更多设置 → 开发者选项」中打开「USB 调试」。
3. 用数据线连接电脑，在手机上允许 USB 调试。

不同系统的菜单名称可能不同。无需解锁 BootLoader 或 root。

## 2. 操作提示词

将以下内容交给 AI 助手：

> 请通过 adb 关闭已连接手机上 `com.mobiletools.systemhelper` 的上报同意开关，并设置后台运行限制。
> 只修改下面指定的两项设置，记录修改前的值。
>
> **准备 adb**
> - 执行 `adb version`。已有 adb 时直接使用。
> - 未安装时，下载 Google 官方 Android SDK Platform-Tools。Windows 下载地址：
>   `https://dl.google.com/android/repository/platform-tools-latest-windows.zip`。
>   解压后用绝对路径调用，无需修改系统 PATH。
>
> **确认设备和应用**
> - 执行 `adb devices`。只有一台设备且状态为 `device` 时继续；否则报告连接状态，等待用户指定设备或完成授权。
> - 执行 `adb shell pm path com.mobiletools.systemhelper`，确认包存在。
> - 执行 `adb shell dumpsys package com.mobiletools.systemhelper`，记录版本和当前用户的 UID。
> - 读取 `operator_service_improve_plan` 和 `RUN_ANY_IN_BACKGROUND` 的当前值。
>
> **修改设置**
> ```bash
> adb shell settings put secure operator_service_improve_plan 0
> adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
> ```
>
> **验证结果**
> ```bash
> adb shell settings get secure operator_service_improve_plan
> adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
> ```
> - 预期分别返回 `0` 和 `ignore`。原值已符合要求时，无需重复修改。
> - 如需观测流量，读取 `adb shell dumpsys netstats detail` 中该 UID 的 `UID stats`，汇总全部时间桶的
>   `rb` 和 `tb`；不要叠加 `UID tag stats`。间隔 20 秒再读取一次，报告差值。
> - 不要执行卸载、停用、root、解锁或刷机操作。
>
> 最后列出两项设置修改前后的值、命令结果和流量观测时段。未执行的检查写明未执行。

## 3. 预期结果

| 检查项 | 预期结果 |
|---|---|
| `operator_service_improve_plan` | `0` |
| `RUN_ANY_IN_BACKGROUND` | `ignore` |
| 流量检查（如执行） | 列出观测时段及上、下行差值 |

设置值符合预期，表示两项配置已写入。短时流量无增量不代表永久停止上报。
恢复命令见 [处置方法](mitigation.md#5-恢复)。
