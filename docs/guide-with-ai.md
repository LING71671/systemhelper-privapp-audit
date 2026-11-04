# 用 AI 助手设置后台限制

这份 APK 的小米分支不检查上报同意开关。下面操作设置后台运行限制。
代码依据见 [深度核对报告](verification_zh.md)。

## 1. 连接手机

1. 在「设置 → 我的设备 → 全部参数与信息」中连续点击 OS 版本 7 次，开启开发者模式。
2. 在「设置 → 更多设置 → 开发者选项」中打开「USB 调试」。
3. 用数据线连接电脑，在手机上允许 USB 调试。

不同系统的菜单名称可能不同。需要能在电脑上执行命令的 AI 助手。

## 2. 操作提示词

> 请通过 adb 为 `com.mobiletools.systemhelper` 设置后台运行限制。
>
> **准备和确认**
> - 执行 `adb version`；未安装时使用 Google 官方 Android SDK Platform-Tools。
> - 执行 `adb devices`。只有一台已授权设备时继续；否则报告连接状态，等待用户处理。
> - 执行 `adb shell pm path com.mobiletools.systemhelper`，确认应用存在。
> - 读取应用版本、当前用户 UID 和 `RUN_ANY_IN_BACKGROUND` 原值。
>
> **设置后台限制**
> ```bash
> adb shell cmd appops set com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND ignore
> adb shell cmd appops get com.mobiletools.systemhelper RUN_ANY_IN_BACKGROUND
> ```
> 原值已为 `ignore` 时，无需重复修改。
>
> **验证和报告**
> - 读取 `device_provisioned` 和 `operator_service_improve_plan`，不修改它们。
> - 每次先执行 `adb shell dumpsys netstats --poll`，确认刷新成功，再读取 `dumpsys netstats detail`。
> - 只汇总目标 UID 的 `UID stats` 全部时间桶，不叠加 `UID tag stats`。间隔采样，报告时间和差值。
> - 如启动服务，记录退出码和实际进程状态。
> - 不执行卸载、清除数据、root、解锁或刷机，不额外修改联网控件。
>
> 最后给出后台限制修改前后的值、观测时段、流量差值和未执行的检查。

## 3. 结果含义

`ignore` 表示后台限制已写入。流量无增量表示观测期间统计未增加。
手机端联网入口和恢复命令见 [处置方法](mitigation.md)。
