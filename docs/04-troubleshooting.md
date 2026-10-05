# 04 · Troubleshooting / 故障排查

## English

### Fast triage

```sh
free                                   # 1. memory first — always
/etc/init.d/mihomo status              # 2. is the service up?
logread | grep -i crashcore | tail -30 # 3. what does the core say?
curl -s http://127.0.0.1:9990/version  # 4. is the API answering?
nft list table ip mihomo               # 5. are the rules loaded?
cat /tmp/mihomo-status                 # 6. what did the launcher think?
```

### Symptom → cause → fix

| Symptom | Most likely cause | Fix |
|---|---|---|
| Ping works, **SSH/web time out** | RAM exhausted (the classic freeze) | Power-cycle. Then lower `GOMEMLIMIT` / trim rules — see §1 below |
| Everything unreachable | Core not running | `/etc/init.d/mihomo restart`, check `logread` |
| Only proxied sites fail | Proxy pool dead or config empty | Switch node in the dashboard, or re-run the subscription update |
| Only direct sites fail | Bad direct rule, or DNS broken | Check the DNS section, verify `:1053` is listening |
| Dashboard loads, no nodes | Subscription body was the wrong format | The CGI extracts `proxies:`; verify with `awk` |
| After config change nothing happens | Update succeeded but the core did not restart | `sh /overlay/mihomo/restart.sh` |
| Service dies when you log out | Started with `nohup`/`&` instead of procd | Install `/etc/init.d/mihomo` and `enable` it |
| Config lost after reboot | It was only in `/tmp` | Keep the source of truth in `/overlay` |
| Device won't boot, LED solid | Flash write was interrupted | Recovery mode + TFTP (see below) |
| `xz: not found` | Missing package | `opkg update && opkg install xz` |
| Decompressed core is 0 bytes / too small | tmpfs ran out of space | Check the space guard; free RAM or shrink the core |

### §1 The RAM exhaustion pattern (most important)

**Signature:** `ping` replies, TCP ports even accept, but **every** session times out
and the load average climbs with no visible user process.

```sh
free                    # free is tiny
cat /proc/loadavg       # load is high
top                     # no single process explains it
```

**Why:** the kernel is spending all its time reclaiming pages. Userspace cannot get
scheduled, so even trivial commands time out.

**Immediate fix:** power-cycle.

**Real fix:** reduce the budget.

```
1. confirm the guards are actually applied
     grep -r GOGC /etc/init.d/mihomo /overlay/mihomo/*.sh
2. lower them if needed
     GOMEMLIMIT=16MiB   (from 20MiB)
3. shrink the rule set
     keep DOMAIN-SUFFIX,cn,DIRECT and drop broad enumeration
4. re-check with free after a restart, before adding anything else
```

### Recovery when it will not boot

```sh
# 1. enter the bootloader's recovery mode
#    unplug power → hold Reset → plug in while holding → keep 8-10 s
# 2. run the bundled server (root required)
sudo python3 recovery/tftp-recovery.py stock-firmware.bin en14
# 3. after the transfer, DO NOT cut power for 10-15 minutes
```

> If the bootloader only accepts vendor-format images, flash the stock firmware,
> boot it, regain root, then write OpenWrt with `mtd`.

### Safety valves to keep

- Keep `mtd1`–`mtd6` backups somewhere off the device.
- `mtd4` (Factory) contains radio calibration — losing it degrades WiFi forever.
- Keep a USB-TTL adapter: it turns "brick" into "20 minutes".

---

## 中文

### 快速定位

```sh
free                                   # 1. 先看内存，永远先看内存
/etc/init.d/mihomo status              # 2. 服务在不在
logread | grep -i crashcore | tail -30 # 3. 内核说了什么
curl -s http://127.0.0.1:9990/version  # 4. API 有没有响应
nft list table ip mihomo               # 5. 规则加载了吗
cat /tmp/mihomo-status                 # 6. 启动脚本的判断结果
```

### 现象 → 原因 → 处理

| 现象 | 最可能的原因 | 处理 |
|---|---|---|
| ping 通但 **SSH/网页全部超时** | 内存耗尽（经典假死）| 拔插电源；然后调低 `GOMEMLIMIT` / 精简规则 —— 见下面 §1 |
| 全部不通 | 内核没运行 | `/etc/init.d/mihomo restart`，看 `logread` |
| 只有代理目标失败 | 线路池失效或配置为空 | 在面板切换线路，或重新更新订阅 |
| 只有直连目标失败 | 直连规则写错，或 DNS 异常 | 检查 DNS 段，确认 `:1053` 在监听 |
| 面板能开但没有线路 | 订阅内容格式不对 | CGI 只提取 `proxies:` 段，用 `awk` 验证 |
| 改了配置但没生效 | 更新成功但内核没重启 | `sh /overlay/mihomo/restart.sh` |
| 一登出服务就消失 | 用了 `nohup`/`&` 而不是 procd | 安装 `/etc/init.d/mihomo` 并 `enable` |
| 重启后配置没了 | 只存在于 `/tmp` | 把可信来源放在 `/overlay` |
| 设备开不了机、指示灯常亮 | 闪存写入被中断 | 进入恢复模式 + TFTP（见下）|
| `xz: not found` | 缺包 | `opkg update && opkg install xz` |
| 解压后内核是 0 字节 / 太小 | 内存盘空间不足 | 检查空间预检；释放内存或换更小的内核 |

### §1 内存耗尽的特征（最重要）

**特征**：`ping` 有回、端口甚至能连上，但**所有**会话都超时，
负载持续升高却看不到占用它的用户进程。

```sh
free                    # 空闲极小
cat /proc/loadavg       # 负载很高
top                     # 却没有任何进程能解释
```

**原因**：内核把所有时间都花在回收内存页上，用户态拿不到调度，
连最简单的命令都会超时。

**立即处理**：拔插电源。

**真正修复**：降低预算。

```
1. 确认保护参数真的生效了
     grep -r GOGC /etc/init.d/mihomo /overlay/mihomo/*.sh
2. 必要时调低
     GOMEMLIMIT=16MiB   （原来是 20MiB）
3. 精简规则集
     保留 DOMAIN-SUFFIX,cn,DIRECT，去掉大范围枚举
4. 重启后用 free 复核，确认健康了再加别的东西
```

### 开不了机时的救砖

```sh
# 1. 进入引导程序的恢复模式
#    拔电源 → 按住 Reset → 保持按住插电 → 继续按 8-10 秒
# 2. 运行仓库自带服务器（需要 root）
sudo python3 recovery/tftp-recovery.py stock-firmware.bin en14
# 3. 传输完成后 10-15 分钟内【不要断电】
```

> 如果引导程序只接受厂商格式镜像：先刷回原厂固件 → 启动 → 重新拿到 root
> → 再用 `mtd` 写入 OpenWrt。

### 一定要保留的安全阀

- 把 `mtd1`–`mtd6` 的备份存到设备之外的地方。
- `mtd4`（Factory）含射频校准数据，丢了 WiFi 信号会永久性变差。
- 备一根 USB-TTL 串口线：它能把"变砖"变成"20 分钟搞定"。
