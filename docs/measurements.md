# 运行期实测

采样日期：2026-11-04，时区 UTC+8。设备为 Xiaomi Redmi，Android 16，主用户为 `0`。
本页只使用本轮采集结果。保持现有设置，执行服务启动尝试和统计读取，未重新开放上报、未注入或 hook。

## 1. 应用和设置

| 检查项 | 结果 | 命令 |
|---|---|---|
| 安装位置 | `/system/priv-app/SystemHelper/SystemHelper.apk` | `pm path com.mobiletools.systemhelper` |
| 版本 | `3.0.1-20250311`，versionCode `31` | `dumpsys package com.mobiletools.systemhelper` |
| 主用户 UID | `10101` | 同上，`appId=10101` |
| 当前进程 | 未运行 | `pidof com.mobiletools.systemhelper` 无进程号 |
| Doze 白名单 | 无此包 | `dumpsys deviceidle whitelist` |
| 上报同意开关 | `0` | `settings get secure operator_service_improve_plan` |
| 后台运行限制 | `ignore` | `cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND` |

上述两项设置在本轮连接时已处于关闭或受限状态。

## 2. CPU 和启动次数

从 `dumpsys batterystats com.mobiletools.systemhelper` 的目标进程记录读取：

| 指标 | 数值 |
|---|---|
| 用户态 CPU 时间 | 570 ms |
| 内核态 CPU 时间 | 890 ms |
| 合计 CPU 时间 | 1.46 秒 |
| 进程启动次数 | 7 次 |
| 前台 CPU 时间 | 0 ms |
| `GetSignalInfoReceiver` 唤醒闹钟计数 | 0 次 |

系统本轮电池统计显示电池供电时长为 6 小时 36 分 51 秒。CPU 时间和启动次数是系统累计记录，
不是本次 180 秒观测期间产生的增量。本次未测量耗电量或流畅度变化。

## 3. 网络流量

14:52:46 至 14:55:46，每隔约 30 秒读取一次，共 7 个采样点。
每次先执行 `dumpsys netstats --poll`，确认返回 `Forced poll`，再读取 `dumpsys netstats detail`。
只汇总 `UID stats` 中 `uid=10101` 的全部时间桶，共 4 条网络记录、23 个时间桶，不叠加 `UID tag stats`。

| 指标 | 14:52:46 | 14:55:46 | 180 秒差值 |
|---|---|---|---|
| 下行字节 `rb` | 510,307 B | 510,307 B | 0 B |
| 上行字节 `tb` | 138,942 B | 138,942 B | 0 B |
| 下行包数 `rp` | 808 | 808 | 0 |
| 上行包数 `tp` | 857 | 857 | 0 |

7 个采样点的统计一致，未发现该应用或其 `:remote` 进程。期间开关保持为 `0`，后台限制保持为 `ignore`。
两次服务启动均失败，结果列在第 6 节。

这里统计整个 UID 的流量，包含业务代码和定位 SDK。具体请求内容未抓取。

## 4. 闹钟

`dumpsys alarm` 中仍存在以下记录，均为 `ELAPSED_WAKEUP`，`window=0`，
`exactAllowReason=permission`：

| 目标接收器 | 抓取时的 `whenElapsed` |
|---|---|
| `GetSignalInfoReceiver` | −6 分 34 秒 |
| `AppInfoRegisterReceiver` | +3 小时 19 分 40 秒 |
| `SignalInfoRegisterReceiver` | +11 小时 0 分 35 秒 |
| `ScheduleRegisterReceiver` | +11 小时 22 分 20 秒 |

负值表示该记录的计划时间早于抓取时刻。这些闹钟记录在抓取时仍然存在。

## 5. 无法读取的内容

| 检查 | 返回结果 |
|---|---|
| `ls /data/user/0/com.mobiletools.systemhelper/shared_prefs` | `Permission denied` |
| `ls /data/user/0/com.mobiletools.systemhelper/databases` | `Permission denied` |
| `run-as com.mobiletools.systemhelper id` | `package not debuggable` |

本轮未读取到实际 `serverAddress`、本地缓存或历史队列，因此未确认接收服务器和历史上报次数。

## 6. 主动启动尝试

保持 `operator_service_improve_plan=0` 和 `RUN_ANY_IN_BACKGROUND=ignore`，分别执行：

| 命令 | 返回结果 |
|---|---|
| `am start-foreground-service --user 0 -n com.mobiletools.systemhelper/.service.RegisterHelperService` | 退出码 255；`Not found; no service started.` |
| `am startservice --user 0 -n com.mobiletools.systemhelper/.service.RegisterHelperService` | 退出码 255；`app is in background uid null` |

包管理器仍能解析出该服务，应用进程未出现；服务记录中 `app=null`。
前一种失败的具体原因未确认，后一种明确报告后台启动被拒绝。
测试期间后台限制保持不变。

代码显示 `RegisterHelperService` 用于 Binder 配置和电话状态监听初始化，单独启动不等于触发注册上报。
本轮没有成功执行完整上报流程。另一个只调用原始判断方法的 `app_process` 探针被终止（退出码 137），
没有产生结果。

## 7. 系统联网控制入口

实际打开 `SystemHelper → App info → Network access`，页面显示 SIM 1、SIM 2、WLAN 均为开启状态。
本轮未切换这些控件。

脱敏结构化记录见 [证据文件](evidence/verification-2026-11-04.json)，结论见 [深度核对报告](verification_zh.md)。
