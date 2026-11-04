# 运行期实测

采样日期：2026-11-04，时区 UTC+8。设备为 Xiaomi Redmi，Android 16，主用户为 `0`。
本页只使用本轮采集结果。通过 adb 读取系统状态，未修改设置、未手动启动服务、未注入或 hook。

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
不是本次 20 秒观测期间产生的增量。本次未测量耗电量或流畅度变化。

## 3. 网络流量

读取 `dumpsys netstats detail`，只汇总 `UID stats` 中 `uid=10101` 的全部时间桶。
共 4 条网络记录、23 个时间桶，不叠加 `UID tag stats`。

| 指标 | 14:25:02 | 14:25:22 | 20 秒差值 |
|---|---|---|---|
| 下行字节 `rb` | 510,307 B | 510,307 B | 0 B |
| 上行字节 `tb` | 138,942 B | 138,942 B | 0 B |
| 下行包数 `rp` | 808 | 808 | 0 |
| 上行包数 `tp` | 857 | 857 | 0 |

20 秒内，该 UID 的系统流量统计没有增加。两次读取之间未手动触发注册服务，
因此本轮没有验证「主动触发后是否发送」。

累计统计不代表完整使用历史，也不能区分业务上报和定位 SDK 流量。
本次没有逐请求抓包，不能由短时统计推算每天上报次数或保证后续始终不发送。

## 4. 闹钟

`dumpsys alarm` 中仍存在以下记录，均为 `ELAPSED_WAKEUP`，`window=0`，
`exactAllowReason=permission`：

| 目标接收器 | 抓取时的 `whenElapsed` |
|---|---|
| `GetSignalInfoReceiver` | −6 分 34 秒 |
| `AppInfoRegisterReceiver` | +3 小时 19 分 40 秒 |
| `SignalInfoRegisterReceiver` | +11 小时 0 分 35 秒 |
| `ScheduleRegisterReceiver` | +11 小时 22 分 20 秒 |

负值表示该记录的计划时间早于抓取时刻。闹钟记录仍存在，不代表它已成功执行。
`RUN_ANY_IN_BACKGROUND=ignore` 也不能据此解释为所有闹钟均已取消。

## 5. 无法读取的内容

| 检查 | 返回结果 |
|---|---|
| `ls /data/user/0/com.mobiletools.systemhelper/shared_prefs` | `Permission denied` |
| `ls /data/user/0/com.mobiletools.systemhelper/databases` | `Permission denied` |
| `run-as com.mobiletools.systemhelper id` | `package not debuggable` |

本轮未读取到实际 `serverAddress`、本地缓存或历史队列，因此未确认接收服务器和历史上报次数。
