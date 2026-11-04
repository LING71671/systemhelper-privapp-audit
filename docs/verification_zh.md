[English](verification.md)

# 上报关闭效果核对

日期：2026-11-04，UTC+8。对象为一台 Xiaomi Redmi（Android 16）上的 `com.mobiletools.systemhelper`。
本报告使用本轮重新提取的 APK、原始 DEX、jadx 反编译结果和手机实测。

## 结论

手机上看，进程没有运行，连续 3 分钟也没有新增流量；普通后台服务启动被系统拒绝。
但代码里的小米分支只检查开机向导是否完成，没有读取 `operator_service_improve_plan`。
这次看起来停了，并不是代码响应了这个开关。

联网控制页上，SIM 1、SIM 2、WLAN 仍显示开启。本次没有改动这些控件。

## 样本

| 项目 | 值 |
|---|---|
| versionName / versionCode | `3.0.1-20250311` / `31` |
| APK SHA256 | `5267008ede808c467988df588915791d21a6f1f3fbe219c57b125a235000df4f` |
| DEX SHA256 | `f6bee7fba7a94241b1f4b1e41f866dd04292d7e909cce387cf8b0044f79c4fba` |
| 当前用户 / UID | `0` / `10101` |
| 厂商 / Android | `Xiaomi` / `16` |

## 代码中的判断

发送线程 `com.mobiletools.systemhelper.control.g` 和历史重传线程 `control.e` 检查静态变量
`Lc/d/a/b/d;->e:Z`。日志将它称为 `isUserPermissionOpen`。

小米分支 `Lc/d/a/a/l;->a(Context, DeviceInfo)` 调用 `d(Context)` 后，将结果写入该变量。
`d(Context)` 只读取 `Settings.Global.device_provisioned`，判断值是否为 `1`。
原始 DEX 确认该函数没有读取 `Settings.Secure`，赋值位置为小米读取方法的第 7 个 code unit。

本机 `device_provisioned=1`，因此该路径可把内存判断设为 `true`，与同意开关为 `0` 无关。

## 同一份 APK 的厂商对照

| 分支 | 判断来源 | 同意开关为 0 的作用 |
|---|---|---|
| vivo | `a/j.d(Context)`：向导完成且同意开关为 1 | 该判断变为 false；未在 vivo 手机实测 |
| Xiaomi | `a/l.d(Context)`：只检查向导完成 | 不阻止该路径 |
| OPPO、samsung | `a/d.d(Context)`、`a/h.d(Context)`：只检查向导完成 | 不阻止该路径 |
| Liantong、nubia、OnePlus、PTAC、realme、TDTECH、WIKO、ZTE | 调用基础读取流程 `a/a.b(Context)`，非 vivo 路径只检查向导完成 | 不阻止该路径 |

基础读取函数本身对 vivo 作额外分流。厂商选择由 `a/n.c()` 中的厂商属性映射决定。
这里比较的是同一份 APK 的 12 个分支。手机实测只在这台小米上进行。

## 动态检查

| 检查 | 结果 | 可支持的结论 |
|---|---|---|
| 上报同意开关 | `0` | 设置值已写入，不代表小米分支会使用它 |
| 后台限制 | `RUN_ANY_IN_BACKGROUND: ignore` | 当前 AppOp 状态受限 |
| 普通服务启动 | 退出码 255，`app is in background uid null` | 这次后台启动被拒绝 |
| 前台服务启动请求 | 退出码 255，`Not found; no service started.` | 未成功启动；具体失败原因未确认 |
| 180 秒流量观测 | 7 个采样点，上下行与包数均无增量；未发现应用及 `:remote` 进程 | 该 UID 在观测期间无统计增量 |

每次流量读取前强制刷新，返回 `Forced poll`。统计只汇总 `UID stats`，排除重复的 `UID tag stats`。
测试时保持原设置，两次启动都失败了，没有成功触发完整注册流程。

## 辅助服务与默认地址

`RegisterHelperService` 是 Binder 辅助接口，可设置服务器、间隔和日志。
它的 `onCreate` 初始化电话状态监听，未覆盖 `onStartCommand`；单独启动它不等于触发注册上报。

`http://dm.wo.com.cn:18080/register` 是配置字段 `a/b/d.l` 的 DEX 编码静态初值。
`a/b/l.h(Context)` 在配置缺失时使用它。这个值保存在静态字段中，方法内字符串扫描会漏掉它。
本机私有配置仍不可读，实际生效的地址尚未确认。

## 复核方法

```bash
python scripts/verify_gates.py unpack/classes.dex > gate-verification.json
```

脚本提取目标方法的设置调用、厂商判断调用、静态字段写入及编码静态初值。
jadx 本轮报告 4 个错误，关键小函数另用原始 DEX 核对。
只调用原始判断方法的 `app_process` 探针返回退出码 137，没有产生结果。
本次完成了代码检查、服务启动尝试和 3 分钟流量观测，未解密抓包或测试重启。

## 脱敏证据

[结构化记录](evidence/verification-2026-11-04.json) 包含样本哈希、方法名、汇总流量、错误码和设置状态。
未收录设备序列号、IMEI / IMSI / ICCID 实际值、SSID / BSSID、IP、账号、聊天内容、本机路径或 API Key 值。
APK、完整反编译结果和未经筛选的设备输出不进入仓库。
