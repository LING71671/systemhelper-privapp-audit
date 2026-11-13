# 处置方法：后台限制、联网控制与用户级卸载

这份 APK 的小米分支没有读取 `operator_service_improve_plan`。本机目前设置了后台限制，
普通服务启动被系统拒绝。厂商差异见 [深度核对报告](verification_zh.md)。

**推荐路径是第 6 节的用户级卸载**：不动系统分区，效果比后台限制彻底，一条命令即可恢复。
后台限制（第 2 节）适合无法卸载、或需要保留运营商功能的情况。

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

## 6. 推荐：用户级卸载（免 root）

第 2 节只限制后台启动；这一节把组件从用户下卸载。它不动系统分区，效果比 AppOps 更彻底，
恢复成本是一条命令。**建议优先采用本节，后台限制作为不便卸载时的退路。**

### 6.1 实测环境

| 项目 | 值 |
|---|---|
| 机型 / 代号 | Xiaomi 15 Ultra / `xuanyuan` |
| 型号 | `25019PNF3C` |
| 系统 | HyperOS `3.0.314.0.WOACNXM` / Android 16 |
| root | 未 root，仅 ADB |
| 组件版本 | `4.0.0-20260610` / 34，minSdk 31，targetSdk 34 |
| 包标记 | `SYSTEM HAS_CODE ALLOW_CLEAR_USER_DATA` |
| 安装路径 | `/system/priv-app/SystemHelper/SystemHelper.apk` |
| 用户 | 0 主用户、10 隐私空间、999 XSpace |

本轮版本高于仓库样本（`3.0.1-20250311` / 31），说明该组件仍在随系统更新分发。

### 6.2 操作前记录

```bash
adb shell pm path com.mobiletools.systemhelper
adb shell dumpsys package com.mobiletools.systemhelper | grep -E "versionName|userId|installed="
for u in 0 10 999; do adb shell pm list packages --user $u | grep com.mobiletools.systemhelper; done
```

本机 0、10 已安装，999 未安装。记录结果用于判断后续回滚范围。

### 6.3 卸载

```bash
adb shell pm uninstall --user 0 com.mobiletools.systemhelper
adb shell pm uninstall --user 10 com.mobiletools.systemhelper
```

预期返回 `Success`。本机 0、10 均返回 `Success`。
对未安装的用户重复执行会返回 `Failure [not installed for N]`，不影响其他用户。

### 6.4 验证

| 检查项 | 命令 | 预期 | 本机实测 |
|---|---|---|---|
| 用户态已卸载 | `pm list packages --user 0 \| grep com.mobiletools.systemhelper` | 无输出 | 无输出 |
| 三个用户均不在 | 对 0、10、999 重复上一行 | 均无输出 | 均无输出 |
| 状态位 | `dumpsys package … \| grep installed=` | `installed=false` | 三个用户均 `installed=false` |
| 进程 | `pidof com.mobiletools.systemhelper` | 无输出 | 无输出 |
| 系统镜像仍在 | `pm list packages -u --user 0 \| grep …` | 仍可见 | 仍可见 |
| 崩溃 | `logcat -b crash` | 无新增 | 无新增 |

`pm list packages -u` 仍列出该包，说明只移除了用户态安装，`/system/priv-app` 原件未动。

### 6.5 恢复

```bash
adb shell cmd package install-existing --user 0 com.mobiletools.systemhelper
```

预期返回 `Package com.mobiletools.systemhelper installed for user: 0`。
本轮未执行恢复；命令语法与 `cmd package` 帮助一致，首次使用时建议先在一个用户上验证。

### 6.6 边界

- 系统分区副本未删除；能重新执行安装的系统组件仍可把它恢复。
- OTA、恢复出厂可能把组件带回，升级后需复查。
- 未验证：重启后的持久性、双卡切换、运营商自注册业务、长期稳定性。
- 个别设备启用了企业策略或“查找设备”时可能拒绝卸载，需按返回的错误码单独判断。

### 6.7 同机可一并处理的相邻组件（可选）

以下组件与本包无直接关系，仅因同属遥测或推广面而记录，供参考：

| 包名 | 用途 | 本轮处置 |
|---|---|---|
| `com.miui.analytics` | 系统统计埋点 | 已按用户卸载（0、10） |
| `com.miui.systemAdSolution` | 广告 SDK | 已按用户卸载（0、10） |
| `com.miui.misightservice` | 体验上报（APK 部分） | 已按用户卸载；`/system_ext/bin/misight` 原生守护进程仍在 |
| `com.miui.uireporter` | UI 上报 | 已按用户卸载（0、10） |
| `com.xiaomi.ugd` | 用户增长/推广 | 已按用户卸载（0、10） |
| `com.android.adservices.api` 等三个 | 隐私沙盒广告 | 已按用户卸载（0、10） |

不同机型与 HyperOS 版本的可用性不同；售后类 `com.xiaomi.ab` 本轮保留。
