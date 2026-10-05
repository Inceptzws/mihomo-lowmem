# 03 · Installation ★ / 安装步骤与顺序 ★

> **ORDER MATTERS. Read all 9 stages before touching anything.**
> **顺序很重要。动手之前请把 9 个阶段全部读完。**

---

## At a glance / 总览

| # | Stage / 阶段 | Why this position / 为什么在这个位置 |
|---|---|---|
| 0 | Prepare tools & firmware / 准备工具与固件 | nothing else can start without this |
| 1 | Identify hardware & firmware / 确认硬件与固件 | wrong image = brick |
| 2 | **Back up every flash partition** / 备份所有闪存分区 | the only way back |
| 3 | Gain root / 取得 root | needed to write flash |
| 4 | Write OpenWrt / 写入 OpenWrt | **destructive** — backups must exist |
| 5 | First boot + LAN/WiFi / 首次启动与网络 | gives you a stable management path |
| 6 | Install dependencies (`xz`) / 安装依赖 | the core cannot be decompressed without it |
| 7 | Deploy core + config + service / 部署内核与配置 | **memory guards go in here, not later** |
| 8 | Verify memory & proxy / 验证内存与代理 | prove it is healthy before adding rules |
| 9 | Load nftables rules **last** / 最后加载 nftables 规则 | a broken rule set must not lock you out |

> ⚠️ **The two most common ways to destroy a working setup:**
> 1. Starting the core **without** the memory guards → the system freezes mid-configuration.
> 2. Loading the transparent-proxy rules **before** the proxy works → LAN clients lose
>    connectivity and you can no longer reach the router to fix it.
>
> ⚠️ **最常见的两种自毁方式：**
> 1. **没有**加内存保护参数就启动内核 → 配置到一半系统卡死。
> 2. 在代理可用**之前**就加载透明代理规则 → 局域网设备断网，
>    你也再连不上路由器去修。

---

## English

### Stage 0 · Prepare

**Hardware**

- The router, a wired connection to its **LAN** port (not WAN — recovery modes use LAN)
- A USB-TTL serial adapter is **strongly recommended** for recovery (CH340 class)
- A computer with `ssh`, `scp`, `xz`, and a TFTP-capable network stack

**Software**

```sh
# Build the core (or download a release / build it yourself)
cd build && ./build-mihomo.sh
# produces: CrashCore.xz (~5.9 MB, 2 MiB dictionary)
```

**Firmware**

- `openwrt-<target>-squashfs-sysupgrade.bin` for **your exact model**
  (for MT7621A devices: `ramips/mt7621`)
- The **stock** firmware image for your model, kept aside for recovery
- **Backup images of every partition** (stage 2)

> Double-check the target. Writing another model's image produces a brick that
> requires a serial console to recover.

### Stage 1 · Identify hardware & firmware

```sh
# on the stock firmware, over SSH/telnet
cat /proc/cpuinfo                     # confirm SoC
cat /proc/mtd                         # partition layout
uname -a
```

Record the partition table — you will need the **exact** `mtd` names in stages 2 and 4.

```
Typical MT7621A 16 MB layout / 典型布局：
  mtd0 ALL        mtd1 Bootloader   mtd2 Config
  mtd3 Bdata      mtd4 Factory      mtd5 crash      mtd6 cfg_bak
  mtd7 overlay    mtd8 OS1          mtd9 rootfs     mtd10 disk
```

**Check whether your firmware version is exploitable.** Vendors patch the
vulnerability used in stage 3; if yours is patched, either downgrade first or use
the serial/recovery route.

### Stage 2 · Back up every flash partition ★ do not skip

```sh
# for each mtd block you care about (at minimum 1-6, and 4 = radio calibration!)
dd if=/dev/mtd1 of=/tmp/mtd1_bootloader.bin
dd if=/dev/mtd4 of=/tmp/mtd4_factory.bin     # ← contains radio calibration
# ... repeat, then pull them off the device
scp root@ROUTER:/tmp/mtd*.bin ./
```

> **`mtd4` (Factory) holds your radio calibration data.** Losing it means weak or
> dead WiFi forever. Back it up before writing anything.
>
> **`mtd4`（Factory）保存着射频校准数据。** 丢了就再也无法恢复信号强度。
> 写任何东西之前先备份。

### Stage 3 · Gain root

Use whichever applies to your device/firmware:

| Route | When |
|---|---|
| Known exploit for an unpatched firmware | simplest; needs the web UI reachable |
| Serial console (U-Boot) | always available; needs a USB-TTL adapter |
| Vendor's own recovery/TFTP mode | when the device still boots its bootloader |

**Do not proceed** until you have a working root shell. Verify:

```sh
id            # uid=0(root)
ls /proc/mtd  # partitions visible
```

### Stage 4 · Write OpenWrt (destructive)

```sh
# copy the image to the device
scp openwrt-*.bin root@ROUTER:/tmp/openwrt.bin

# verify it arrived intact — compare with the local md5!
md5sum /tmp/openwrt.bin

# write to the firmware partition (name it exactly as in /proc/mtd)
/sbin/mtd -e OS1 -r write /tmp/openwrt.bin OS1
```

> ⚠️ Run the write **detached** so a dropped SSH session cannot interrupt it:
> ```sh
> ( /sbin/mtd -e OS1 -r write /tmp/openwrt.bin OS1 > /tmp/flash.log 2>&1 & )
> ```
> A killed erase/write leaves the flash half-written.
>
> ⚠️ 用**后台**方式执行写入，避免 SSH 断线打断：
> 被中断的擦写会留下写了一半的闪存。

**Warning:** some bootloaders accept *only* vendor-format images over their TFTP
recovery mode and will not boot a raw OpenWrt image. If recovery is the only route,
flash the vendor image first, boot it, then get root and use `mtd`.

### Stage 5 · First boot, LAN and WiFi

OpenWrt's default is `192.168.1.1` with no root password.

```sh
# set a LAN address you like, enable both radios, set country + channels
uci set network.lan.ipaddr='192.168.1.1'
uci set wireless.radio0.disabled='0'; uci set wireless.radio0.country='CN'
uci set wireless.radio0.channel='1'
uci set wireless.default_radio0.ssid='YOUR_SSID'
uci set wireless.default_radio0.encryption='psk2'
uci set wireless.default_radio0.key='YOUR_PASSWORD'
uci set wireless.radio1.disabled='0'; uci set wireless.radio1.country='CN'
uci set wireless.radio1.channel='48'      # 5 GHz
uci set wireless.default_radio1.ssid='YOUR_SSID_5G'
uci set wireless.default_radio1.encryption='psk2'
uci set wireless.default_radio1.key='YOUR_PASSWORD'
uci commit

# install your SSH public key so later steps do not need password auth
mkdir -p /root/.ssh && chmod 700 /root/.ssh
echo 'ssh-ed25519 AAAA... you@host' > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# set a root password, then apply
passwd root
( sleep 3; /etc/init.d/network restart; wifi reload ) &
```

> Use an **ed25519** key. Many embedded dropbear builds reject RSA/SHA-1 keys
> by default, which looks like "my key is ignored".
>
> 请用 **ed25519** 密钥。许多嵌入式 dropbear 默认拒绝 RSA/SHA-1 密钥，
> 表现为"密钥被无视"。

### Stage 6 · Install dependencies

```sh
# point opkg at a fast mirror if needed
sed -i 's|downloads.openwrt.org|mirrors.tuna.tsinghua.edu.cn/openwrt|g' /etc/opkg/distfeeds.conf
opkg update
opkg install xz                     # REQUIRED: decompresses the core
which xz                            # must print a path
```

> `xz-utils` is a meta-package; the binary lives in `xz`.
> `xz-utils` 是元包，真正的二进制在 `xz` 包里。

### Stage 7 · Deploy core, config and service ★

```sh
# --- 7.1 layout on the router / 路由器上的目录结构 ---
mkdir -p /overlay/mihomo/ui /overlay/mihomo/providers

# --- 7.2 core: compressed on flash / 内核：压缩包放闪存 ---
scp CrashCore.xz  root@ROUTER:/overlay/mihomo/CrashCore.xz
# verify on the device / 在设备上校验
xz -t /overlay/mihomo/CrashCore.xz && echo OK

# --- 7.3 config: split into head + tail for streamed rebuilds ---
#     head = everything before `proxies:`
#     tail = from `proxy-groups:` onwards
awk '/^proxies:/{exit} {print}'                config.yaml > /overlay/mihomo/head.txt
awk 'f{print} /^proxy-groups:/{f=1; print}'    config.yaml > /overlay/mihomo/tail.txt
cp config.yaml /overlay/mihomo/config.yaml

# --- 7.4 scripts, rules, dashboard ---
scp files/start.sh files/restart.sh files/nft.rules root@ROUTER:/overlay/mihomo/
scp -r ui/.                       root@ROUTER:/overlay/mihomo/ui/
scp files/init.d/mihomo           root@ROUTER:/etc/init.d/mihomo
scp files/www/cgi-bin/save-sub    root@ROUTER:/www/cgi-bin/save-sub
chmod 755 /overlay/mihomo/*.sh /etc/init.d/mihomo /www/cgi-bin/save-sub

# --- 7.5 enable autostart / 开机自启 ---
/etc/init.d/mihomo enable

# --- 7.6 FIRST START — memory guards are already inside the service ---
/etc/init.d/mihomo start
sleep 20
free                              # ← the moment of truth / 见分晓的时刻
```

**What you must see**

```
              total        used        free
Mem:         120480       50556       54752     ← >= 15 MB free is healthy
                                           (>= 40 MB is normal)
```

If free memory is under ~10 MB, **stop**: lower `GOMEMLIMIT`, reduce the rule count,
and restart. Do not continue to stage 9 with a starving system.

如果空闲内存低于 10MB，**停下来**：调低 `GOMEMLIMIT`、精简规则数后重启。
不要在系统濒临饿死时进入第 9 阶段。

> The service already sets `GOGC=50 GOMEMLIMIT=20MiB`. These are the guards from
> [01-memory-design.md](01-memory-design.md) — without them the first start can
> freeze the router mid-configuration.
>
> 服务定义里已经包含 `GOGC=50 GOMEMLIMIT=20MiB` —— 这就是
> [01-memory-design.md](01-memory-design.md) 里的保护参数；没有它们，
> 第一次启动就可能把路由器卡死在配置中途。

### Stage 8 · Verify the proxy before touching the firewall

```sh
# API alive?
curl -s http://127.0.0.1:9990/version

# explicit-proxy test (does NOT require nftables yet)
curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}\n' https://example.com
# and a direct test / 再测一个直连目标
curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}\n' https://www.baidu.com
```

Both must return `200` **before** stage 9. If not, fix the config/nodes first —
because after stage 9 a broken proxy means broken LAN connectivity.

两项都必须在第 9 阶段**之前**返回 `200`。否则先修配置/线路 ——
因为第 9 阶段之后，代理不通就等于局域网不通。

### Stage 9 · Transparent proxy rules — LAST

```sh
nft -f /overlay/mihomo/nft.rules
nft list table ip mihomo          # confirm it loaded
```

> If you ever lock yourself out: reboot. `nftables` rules are not persisted unless
> you add them to `rc.local`, so a reboot restores connectivity.
>
> 万一把自己锁在外面：重启即可。除非把规则写进 `rc.local`，
> 否则 nftables 规则不会持久化，重启就恢复连通。

Finally, make boot reproducible:

```sh
# /etc/rc.local — before `exit 0`
/overlay/mihomo/start.sh &
exit 0
```

### Post-install checks

```sh
free                                     # >= 15 MB free
/etc/init.d/mihomo status                # running
curl -s http://127.0.0.1:9990/proxies | head -c 200
nft list table ip mihomo | head
reboot                                   # then confirm it all comes back by itself
```

---

## 中文

### 阶段 0 · 准备

**硬件**

- 路由器，以及一条接到其 **LAN** 口的有线连接（不是 WAN —— 恢复模式走 LAN）
- **强烈建议**准备 USB-TTL 串口线（CH340 级别）用于救砖
- 一台装有 `ssh`、`scp`、`xz` 并能做 TFTP 的电脑

**软件**

```sh
cd build && ./build-mihomo.sh
# 产出：CrashCore.xz（约 5.9MB，2MiB 字典）
```

**固件**

- 与**你确切机型**匹配的 `openwrt-<target>-squashfs-sysupgrade.bin`
  （MT7621A 设备对应 `ramips/mt7621`）
- 同机型的**原厂**固件，留作救砖
- **所有分区的备份镜像**（见阶段 2）

> 务必确认目标机型。刷错机型的镜像会变砖，只能靠串口救回。

### 阶段 1 · 确认硬件与固件

```sh
cat /proc/cpuinfo      # 确认 SoC
cat /proc/mtd          # 分区表
```

把分区表记下来 —— 阶段 2 和 4 需要**精确**的 `mtd` 名称。

**确认你的固件版本是否可被漏洞利用。** 厂商会修补阶段 3 所用的漏洞；
若已修补，请先降级或改用串口/恢复模式路线。

### 阶段 2 · 备份所有闪存分区 ★ 不可跳过

```sh
dd if=/dev/mtd1 of=/tmp/mtd1_bootloader.bin
dd if=/dev/mtd4 of=/tmp/mtd4_factory.bin     # ← 射频校准数据！
# ……逐个备份，然后拉到电脑上
scp root@ROUTER:/tmp/mtd*.bin ./
```

> **`mtd4`（Factory）保存射频校准数据。** 一旦丢失，WiFi 信号将永久性变弱甚至失效。
> 写任何东西之前先备份它。

### 阶段 3 · 取得 root

按你的设备/固件情况选择：

| 路线 | 适用场景 |
|---|---|
| 未修补固件的已知漏洞 | 最简单；需要能访问 Web 管理页 |
| 串口控制台（U-Boot）| 永远可用；需要 USB-TTL 线 |
| 厂商自带恢复/TFTP 模式 | 设备还能进入引导程序时 |

**没拿到 root shell 之前不要继续。** 验证：

```sh
id            # uid=0(root)
ls /proc/mtd  # 能看到分区
```

### 阶段 4 · 写入 OpenWrt（破坏性操作）

```sh
scp openwrt-*.bin root@ROUTER:/tmp/openwrt.bin

# 校验是否完整传输 —— 与本地 md5 对比！
md5sum /tmp/openwrt.bin

# 写入固件分区（名称必须与 /proc/mtd 完全一致）
/sbin/mtd -e OS1 -r write /tmp/openwrt.bin OS1
```

> ⚠️ 请用**后台**方式执行，避免 SSH 断线打断：
> ```sh
> ( /sbin/mtd -e OS1 -r write /tmp/openwrt.bin OS1 > /tmp/flash.log 2>&1 & )
> ```
> 被中断的擦写会留下写了一半的闪存。

**注意**：部分引导程序的 TFTP 恢复模式**只接受**厂商格式镜像，
无法直接引导裸 OpenWrt 镜像。若只能走恢复模式，请先刷回厂商固件、
启动、拿到 root，再用 `mtd` 写入。

### 阶段 5 · 首次启动、LAN 与 WiFi

OpenWrt 默认地址 `192.168.1.1`，root 无密码。

```sh
uci set network.lan.ipaddr='192.168.1.1'
uci set wireless.radio0.disabled='0'; uci set wireless.radio0.country='CN'
uci set wireless.radio0.channel='1'
uci set wireless.default_radio0.ssid='YOUR_SSID'
uci set wireless.default_radio0.encryption='psk2'
uci set wireless.default_radio0.key='YOUR_PASSWORD'
uci set wireless.radio1.disabled='0'; uci set wireless.radio1.country='CN'
uci set wireless.radio1.channel='48'
uci set wireless.default_radio1.ssid='YOUR_SSID_5G'
uci set wireless.default_radio1.encryption='psk2'
uci set wireless.default_radio1.key='YOUR_PASSWORD'
uci commit

mkdir -p /root/.ssh && chmod 700 /root/.ssh
echo 'ssh-ed25519 AAAA... you@host' > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

passwd root
( sleep 3; /etc/init.d/network restart; wifi reload ) &
```

> 请用 **ed25519** 密钥。许多嵌入式 dropbear 默认拒绝 RSA/SHA-1 密钥，
> 表现为"密钥被无视"。

### 阶段 6 · 安装依赖

```sh
sed -i 's|downloads.openwrt.org|mirrors.tuna.tsinghua.edu.cn/openwrt|g' /etc/opkg/distfeeds.conf
opkg update
opkg install xz                     # 必需：用于解压内核
which xz
```

> `xz-utils` 是元包，真正的二进制在 `xz` 包里。

### 阶段 7 · 部署内核、配置与服务 ★

```sh
mkdir -p /overlay/mihomo/ui /overlay/mihomo/providers

scp CrashCore.xz  root@ROUTER:/overlay/mihomo/CrashCore.xz
xz -t /overlay/mihomo/CrashCore.xz && echo OK      # 校验压缩包

# 拆成 head + tail，供流式重建（head = proxies: 之前；tail = proxy-groups: 起）
awk '/^proxies:/{exit} {print}'                config.yaml > /overlay/mihomo/head.txt
awk 'f{print} /^proxy-groups:/{f=1; print}'    config.yaml > /overlay/mihomo/tail.txt
cp config.yaml /overlay/mihomo/config.yaml

scp files/start.sh files/restart.sh files/nft.rules root@ROUTER:/overlay/mihomo/
scp -r ui/.                       root@ROUTER:/overlay/mihomo/ui/
scp files/init.d/mihomo           root@ROUTER:/etc/init.d/mihomo
scp files/www/cgi-bin/save-sub    root@ROUTER:/www/cgi-bin/save-sub
chmod 755 /overlay/mihomo/*.sh /etc/init.d/mihomo /www/cgi-bin/save-sub

/etc/init.d/mihomo enable
/etc/init.d/mihomo start
sleep 20
free                              # ← 见分晓的时刻
```

**必须看到的结果**

```
              total        used        free
Mem:         120480       50556       54752     ← 空闲 ≥15MB 为健康
                                            （≥40MB 属正常）
```

如果空闲内存低于约 10MB，**停下来**：调低 `GOMEMLIMIT`、精简规则数后重启。
不要在系统濒临饿死时进入第 9 阶段。

> 服务定义里已包含 `GOGC=50 GOMEMLIMIT=20MiB` —— 即
> [01-memory-design.md](01-memory-design.md) 的保护参数；没有它们，
> 第一次启动就可能把路由器卡死在配置中途。

### 阶段 8 · 在动防火墙之前先验证代理

```sh
curl -s http://127.0.0.1:9990/version
curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}\n' https://example.com
curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}\n' https://www.baidu.com
```

两项都必须在第 9 阶段**之前**返回 `200`。否则先修配置/线路 ——
因为第 9 阶段之后，代理不通就等于局域网不通。

### 阶段 9 · 透明代理规则（最后一步）

```sh
nft -f /overlay/mihomo/nft.rules
nft list table ip mihomo
```

> 万一把自己锁在外面：重启即可。除非把规则写进 `rc.local`，
> 否则 nftables 规则不会持久化，重启就恢复连通。

最后让开机可复现：

```sh
# /etc/rc.local —— 放在 `exit 0` 之前
/overlay/mihomo/start.sh &
exit 0
```

### 安装后检查

```sh
free                                     # 空闲 ≥15MB
/etc/init.d/mihomo status                # 运行中
curl -s http://127.0.0.1:9990/proxies | head -c 200
nft list table ip mihomo | head
reboot                                   # 然后确认它能自己全部恢复
```

---

## Recovery path / 救砖路线

If the device no longer boots (e.g. solid yellow/amber LED on many Xiaomi models):

许多机型变砖后的表现是**指示灯常亮**（如小米的黄/琥珀色常亮）：

```
1. unplug power, hold Reset, plug power in while still holding,
   keep holding 8-10 s until the LED blinks rapidly
2. keep the ethernet cable in a LAN port (NOT WAN — the bootloader only uses LAN)
3. run the bundled recovery server / 运行仓库自带的恢复服务器：
       sudo python3 recovery/tftp-recovery.py <stock-firmware.bin> <iface>
4. after the transfer completes DO NOT cut power —
   wait 10-15 minutes for the flash write and self-reboot
```

```
1. 拔电源 → 按住 Reset → 保持按住插上电源 → 继续按 8-10 秒直到灯快速闪烁
2. 网线必须插在 LAN 口（不是 WAN —— 引导程序只用 LAN）
3. 运行仓库自带的恢复服务器
4. 传输完成后【不要断电】，等 10-15 分钟让它写完并自行重启
```

See [04-troubleshooting.md](04-troubleshooting.md) for symptom → cause tables.
症状与原因对照表见 [04-troubleshooting.md](04-troubleshooting.md)。
