# 组件分析

本轮从已连接手机重新提取 APK，核对哈希、清单和 DEX。以下为代码及配置分析，
运行状态和流量以 [本轮实测](measurements.md) 为准。

## 1. 基本信息

| 项 | 值 |
|---|---|
| 包名 | `com.mobiletools.systemhelper` |
| 安装位置 | `/system/priv-app/SystemHelper/SystemHelper.apk` |
| versionName | `3.0.1-20250311` |
| versionCode / minSdk / targetSdk | `31` / `31` / `33` |
| APK 大小 | 3,261,815 字节 |
| MD5 | `a3d23cc81ac1954609dd07d124c85d73` |
| SHA1 | `744ec752f4d231650ca22a6881dcaa398470fbc9` |
| SHA256 | `5267008ede808c467988df588915791d21a6f1f3fbe219c57b125a235000df4f` |
| 共享 UID | `sharedUserId="com.mobiletools.systemhelper.uid"`，appId 10101 |

原生库与资产：

| 文件 | 大小 | 说明 |
|---|---|---|
| `lib/arm64-v8a/liblocSDK8b.so` | 368,568 | 百度定位 SDK |
| `lib/arm64-v8a/libindoor.so` | 1,596,896 | 百度室内定位 |
| `classes.dex` | 1,513,428 | 业务逻辑 + SDK |
| `assets/pub.cer` | 596 | 上行报文用的 RSA 公钥 |

## 2. 权限

清单申请 17 项权限。下表为 `dumpsys package` 读取的部分权限及实际授予状态：

| 权限 | 授予时机 | 标志 |
|---|---|---|
| `READ_PRIVILEGED_PHONE_STATE` | 安装时 | 特权应用专属 |
| `READ_PRECISE_PHONE_STATE` | 安装时 | |
| `PACKAGE_USAGE_STATS` | 安装时 | 逐应用使用时长依赖它 |
| `QUERY_ALL_PACKAGES` | 安装时 | 可枚举全部已安装应用 |
| `SCHEDULE_EXACT_ALARM` | 安装时 | 精确定时 |
| `RECEIVE_BOOT_COMPLETED` | 安装时 | 开机拉起 |
| `ACCESS_FINE_LOCATION` | 运行时 | `GRANTED_BY_DEFAULT` |
| `ACCESS_COARSE_LOCATION` | 运行时 | `GRANTED_BY_DEFAULT` |
| `ACCESS_BACKGROUND_LOCATION` | 运行时 | `GRANTED_BY_DEFAULT` + `RESTRICTION_SYSTEM_EXEMPT` |
| `READ_PHONE_STATE` | 运行时 | `GRANTED_BY_DEFAULT` |
| `READ_EXTERNAL_STORAGE` | 运行时 | `GRANTED_BY_DEFAULT` |

上述 5 个危险权限均带 `GRANTED_BY_DEFAULT`。后台定位还带 `RESTRICTION_SYSTEM_EXEMPT`，
表示该权限具有系统豁免标志；仅凭该标志不能判断用户撤回权限后的效果。

清单另外声明了 `usesCleartextTraffic="true"`，允许明文 HTTP。

## 3. 组件与启动流程

```
BOOT_COMPLETED / QUICKBOOT_POWERON
  └─ OnBootReceiver（priority=2147483647）
       ├─ DMApplication.onCreate → 设备信息读取器初始化
       └─ AlarmManager.setExactAndAllowWhileIdle
            ├─ GetSignalInfoReceiver    → 百度定位 → SignalInfo 入库
            ├─ AppInfoRegisterReceiver  → 逐应用时长 + 流量
            ├─ SignalInfoRegisterReceiver
            └─ ScheduleRegisterReceiver → RegisterIntentService → 上报线程
```

已识别的定时调用使用 `setExactAndAllowWhileIdle`（type=2，ELAPSED_WAKEUP），允许在 Doze 下唤醒。

### 导出组件（`exported=true`，无权限保护）

| 组件 | 行为 |
|---|---|
| `Activity/TestActivity` | 界面将设备信息 JSON（含 IMEI/IMSI）显示在 TextView 中 |
| `service/RegisterHelperService` | 提供注册上报入口；本轮未启动 |
| `control/OnBootReceiver` | 高优先级开机接收器 |
| `control/SIMStateReceiver` | 换卡触发 |
| `control/ConnectStateReceiver` | 网络变化触发 |

`TestActivity` 的用途类似调试页面。上述导出声明未设置组件权限；其他应用能否成功调用，还受系统启动限制影响。

## 4. 采集内容

### 4.1 DeviceInfo（约 40 个字段）

```
IMEI1 IMEI2 IMSI1 IMSI2 ICCID1 ICCID2 MNC1 MNC2 CID1 CID2 PCI1 PCI2 TAC1 TAC2
NetworkType1 NetworkType2 5GEnabled1 5GEnabled2 VoNREnable1 VoNREnable2
VolteEnabled1 VolteEnabled2 Manuf Model DeviceType HWVersion SWVersion
OS OSVersion IPv6 ClientVersion SpecVersion RegType DataSlot AccType
SigInfo AppInfo Time
```

厂商适配层按 `ro.product.manufacturer` 派发，覆盖
`Liantong OPPO OnePlus PTAC TDTECH WIKO Xiaomi ZTE nubia realme samsung vivo`
等厂商分支，分别使用对应 API：

- Xiaomi 分支反射 `miui.telephony.TelephonyManager.getImeiForSlot`
- vivo 分支读 `persist.radio.vivo.fiveg`、`persist.vendor.radio.5g_mode_pref`
- 通用兜底反射 `android.os.SystemProperties.get`

设备标识的读取路径随厂商分支变化。

### 4.2 SignalInfo（小区与位置）

```
IMEI IMSI ICCID MNC CID TAC PCI ARFCN RSRP RSRQ SINR
LATITUDE LONGITUDE ALTITUDE SPEED BEARING
NetworkType Bands Bandwidth CQI* CallDisconnectCause Time
```

定位部分：`GetSignalInfoReceiver` 注册百度定位回调，坐标系 `bd09ll`，回调里取经纬度与精度半径，
再合并当前服务小区的 CID/TAC/PCI/RSRP 等，组装成 JSON 落本地库。

判定条件：`MNC` 以 `460` 开头（中国境内网络）才落库。

### 4.3 AppInfo（逐应用使用与流量）

```
pkgName appLabel runTime rx1 rx2 tx1 tx2 totalData1 totalData2 totalDataWiFi Time
```

- `runTime`：`UsageStatsManager.queryAndAggregateUsageStats` → `getTotalTimeInForeground`
- 流量：`NetworkStatsManager.querySummary` 按 UID 遍历 bucket，`getRxBytes` / `getTxBytes`
  分别取 SIM1、SIM2、WiFi 三路
- `appLabel`：`ApplicationInfo.loadLabel`，即应用在桌面上显示的名字
- 过滤掉 `com.android.*` 系统包

这些字段记录应用的前台使用时长，以及对应 UID 的网络流量。

## 5. 上行通道

| 项 | 值 |
|---|---|
| 实现 | `HttpURLConnection` / `HttpsURLConnection`，POST |
| Content-Type | `application/encrypted-json` |
| 报文处理 | 使用 `AES/ECB/PKCS5Padding`、RSA 公钥、MD5 和 Base64 处理报文及相关字段；公钥位于 `assets/pub.cer` |
| 查询串 | `?ver=5.0&manuf=<厂商>&model=<机型>&sign=<签名>` |
| 服务地址 | 读 SharedPreferences 键 `serverAddress` |
| 本地队列 | SQLite `dmregister`（`ID integer primary key`），发送失败落库，由重投线程补发 |

### 关于服务地址

APK 字符串表里存在一个字面量：

```
http://dm.wo.com.cn:18080/register
```

本次扫描未找到引用该字面量的指令。发送逻辑从 SharedPreferences 读取 `serverAddress`，
不能将字符串表中的地址直接视为实际接收服务器。

仅凭本次 APK 分析无法确认实际接收服务器。设备配置位于
`shared_prefs/com_mobiletools_systemhelper_preference.xml`，本次无 root，未能读取。

### 发送条件

发送前依次判断：

1. `device_provisioned == 1`（开机向导已完成）
2. `Settings.Secure.operator_service_improve_plan == 1`（用户侧的「运营商服务改进计划」开关）
3. 网络 MNC 以 `460` 开头，且满足「联通网络 或 WiFi」
4. 定时器到点

关闭第 2 项后，代码会跳过发送流程。本轮读取时该值已为 `0`，未重新触发服务验证。

## 6. 定时参数

从配置类静态初始化中取到的实值：

| 常量 | 值 | 含义 |
|---|---|---|
| `scheduleInterval` | 86,400,000 ms | 注册周期 24 小时 |
| `signalInfoInterval` | 43,200,000 ms | 信号信息周期 12 小时 |
| `GetsignalInfoInterval` | 3,600,000 ms | 定位采集周期 1 小时 |
| 随机打散 | `Random.nextInt(86,400,000)` | 首次触发与重投的偏移 |

## 7. 未确认的行为

- **上传频率**：代码按 1h / 12h / 24h 定时触发，并检查同意开关和网络条件。
  本轮 20 秒观测没有流量增量，不能推算每天的上报次数。
- **缓存门牌级地址**：已识别的上报字段没有地址文本。定位 SDK 中的 `AP` / `CL` 表用于 WiFi 指纹定位；
  应用私有目录未读取，无法确认其中的实际缓存内容。
- **上传 WiFi 名称**：百度 SDK 中存在 `getSSID / getBSSID / getScanResults` 调用，自有上报 JSON 未发现 SSID 字段。
  本次未解密或逐请求核对 SDK 的网络数据，无法确认是否上传 WiFi 名称。
