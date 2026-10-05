# 02 · Architecture / 架构说明

## English

### Runtime layout

```
                     ┌─────────────────────────── Router (OpenWrt) ──────────────────────────┐
                     │                                                                        │
  WAN ── DHCP ──────►│  wan                    ┌──────────────┐                              │
                     │                         │   mihomo     │◄── DNS  :1053                │
  LAN clients ──────►│  br-lan ── nftables ───►│  (procd)     │◄── redir :7892               │
  (WiFi + wired)     │            prerouting   │              │◄── mixed :7890               │
                     │                         │  API :9990   │──► dashboard /ui/            │
                     │                         └──────┬───────┘                              │
                     │                                │ outbound                              │
                     │                         ┌──────┴───────┐                              │
                     │                         │  proxy pool  │                              │
                     │                         └──────────────┘                              │
                     └────────────────────────────────────────────────────────────────────────┘
```

### Where each file lives, and why

| Path | Storage | Survives reboot | Why there |
|---|---|---|---|
| `/overlay/mihomo/CrashCore.xz` | flash | yes | 5.91 MB compressed core |
| `/overlay/mihomo/config.yaml` | flash | yes | source of truth |
| `/overlay/mihomo/head.txt`, `tail.txt` | flash | yes | templates for streamed rebuilds |
| `/overlay/mihomo/nft.rules` | flash | yes | firewall rules |
| `/overlay/mihomo/ui/` | flash | yes | dashboard |
| `/tmp/mihomo/CrashCore` | tmpfs | no | 28.25 MB decompressed core |
| `/tmp/mihomo/config.yaml` | tmpfs | no | working copy |
| `/etc/init.d/mihomo` | flash | yes | procd service definition |
| `/www/cgi-bin/save-sub` | flash-ish (overlay) | yes | subscription receiver |

**Rule of thumb:** big and regenerable → tmpfs. Small and precious → flash.
**原则**：大而可重建的放内存盘，小而珍贵的放闪存。

### Boot sequence

```
power on
  └─ /etc/rc.local
      └─ /overlay/mihomo/start.sh
          ├─ 1. check tmpfs free space     (< 35 MB → abort)
          ├─ 2. xz -d core into tmpfs
          ├─ 3. verify size >= 28,000,000  (truncated → abort)
          ├─ 4. stage config + ui into tmpfs
          ├─ 5. /etc/init.d/mihomo restart  (procd)
          │      └─ GOGC=50 GOMEMLIMIT=20MiB
          ├─ 6. load nftables rules         (non-fatal if it fails)
          └─ 7. write /tmp/mihomo-status
```

Measured: **about 60 s** from power to a working proxy.

### Data flow of the two "surface" features

**A. Rule-based routing / 规则分流**

```
client packet
   → nftables prerouting (br-lan)
       private range?  → return (never proxied)
       tcp             → redirect :7892
       udp/tcp 53      → redirect :1053 (DNS)
   → mihomo reads the *domain* (thanks to the DNS interception)
   → rule match:
        DOMAIN-SUFFIX,cn,DIRECT      ← one rule covers the whole TLD
        <targeted rules>
        MATCH,<group>                ← catch-all
   → either DIRECT (kernel route) or through a proxy outbound
```

**B. Subscription update / 订阅更新**

```
device browser
   │  GET <subscription>            (device's own network; already routed correctly)
   │  POST /cgi-bin/save-sub        (body = whatever the endpoint returned)
   ▼
router CGI
   ├─ cat head.txt            > config.yaml.new
   ├─ awk (stream)            >> extract `proxies:` section
   ├─ count proxies           → refuse if < 3
   ├─ cat tail.txt            >> config.yaml.new
   ├─ mv into place
   └─ ( sleep 1; restart.sh ) &   → ~10 s later the new pool is live
```

Note the router never opens an outbound connection for this. See
[01-memory-design.md](01-memory-design.md) §5.

### Interfaces

| Interface | Port | Scope | Notes |
|---|---|---|---|
| mixed (HTTP+SOCKS) | 7890 | LAN | manual clients |
| transparent redirect | 7892 | LAN | via nftables |
| DNS | 1053 | LAN | via nftables |
| REST API + dashboard | 9990 | LAN | `/ui/` |
| LuCI | 80 | LAN | OpenWrt admin |

---

## 中文

### 运行时布局

见上方示意图（中英文共用）。

### 文件的存放位置与理由

| 路径 | 存储 | 重启保留 | 为什么放这里 |
|---|---|---|---|
| `/overlay/mihomo/CrashCore.xz` | 闪存 | 是 | 5.91MB 压缩内核 |
| `/overlay/mihomo/config.yaml` | 闪存 | 是 | 唯一可信来源 |
| `/overlay/mihomo/head.txt`、`tail.txt` | 闪存 | 是 | 流式重建用模板 |
| `/overlay/mihomo/nft.rules` | 闪存 | 是 | 防火墙规则 |
| `/overlay/mihomo/ui/` | 闪存 | 是 | 管理面板 |
| `/tmp/mihomo/CrashCore` | 内存盘 | 否 | 28.25MB 解压后内核 |
| `/tmp/mihomo/config.yaml` | 内存盘 | 否 | 运行时副本 |
| `/etc/init.d/mihomo` | 闪存 | 是 | procd 服务定义 |
| `/www/cgi-bin/save-sub` | 闪存（overlay）| 是 | 订阅接收接口 |

**原则**：大而可重建的放内存盘，小而珍贵的放闪存。

### 启动顺序

```
上电
  └─ /etc/rc.local
      └─ /overlay/mihomo/start.sh
          ├─ 1. 检查内存盘剩余空间（<35MB 直接放弃）
          ├─ 2. xz 解压内核到内存盘
          ├─ 3. 校验大小 ≥ 28,000,000（截断则放弃）
          ├─ 4. 把配置与面板放到内存盘
          ├─ 5. /etc/init.d/mihomo restart（procd）
          │      └─ GOGC=50 GOMEMLIMIT=20MiB
          ├─ 6. 加载 nftables 规则（失败不影响启动）
          └─ 7. 写入 /tmp/mihomo-status
```

实测：从通电到代理可用约 **60 秒**。

### 两大功能的数据流

**A. 规则分流** —— 见上方英文部分的路径分解。
关键点：DNS 被透明劫持后，内核才能看到**域名**，规则才有意义。

**B. 订阅更新** —— 路由器**从不**为这件事发起对外连接。
它只做：接收 → 流式提取 → 重建配置 → 重启内核（约 10 秒）。
详见 [01-memory-design.md](01-memory-design.md) 第 5 节。

### 接口一览

| 接口 | 端口 | 范围 | 说明 |
|---|---|---|---|
| mixed（HTTP+SOCKS）| 7890 | 局域网 | 手动客户端 |
| 透明重定向 | 7892 | 局域网 | 经 nftables |
| DNS | 1053 | 局域网 | 经 nftables |
| REST API + 面板 | 9990 | 局域网 | `/ui/` |
| LuCI | 80 | 局域网 | OpenWrt 管理页 |
