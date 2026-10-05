# 08 · Launch post / 发布短文

Ready-to-publish introduction. Copy the English or Chinese version as-is, or trim it
to fit the platform. Delete the bracketed placeholders before posting.

可直接发布的介绍短文。英文或中文版都可以整段复制，也可以按平台裁剪。
发布前请替换方括号里的占位内容。

---

## English

### Running a proxy core on a router that has no memory to spare

I have an old Xiaomi Router 4A Gigabit — MT7621A, 128 MB of RAM, 16 MB of flash.
It was sitting in a drawer. I wanted every device on my LAN to route through a proxy
without installing a client on each one, so I flashed OpenWrt and started with mihomo.

It did not work. Not "ran slowly" — it **froze**. Ping still replied, the web UI and
SSH timed out, and `top` showed a load average around 10 with no user process to
blame. The kernel was spending all its time reclaiming pages.

The arithmetic is embarrassingly simple:

```
usable RAM ......................................... 47 MB
mihomo core decompressed ........................... 28.25 MB
runtime heap (default) ............................. ~21 MB
                                                     ──────
                                                    49 MB   > 47 MB
```

So I stopped trying to make the core smaller and started asking a different question:
**which of these jobs does not have to happen on the router at all?**

That reframing produced **[mihomo-lowmem](https://github.com/Inceptzws/mihomo-lowmem)** —
a deployment that fits in the budget instead of fighting it. The numbers after the work:

```
usable RAM ......................................... 47 MB
core decompressed .................................. 28.25 MB
runtime heap (GOGC=50, GOMEMLIMIT=20MiB) ........... ~12 MB
                                                     ──────
                                                    40 MB   < 47 MB
→ measured 24-26 MB free, boots to a working proxy in ~60 s
```

### The five changes that mattered

1. **A small compression dictionary.** `xz -9` uses a 64 MiB dictionary, so *decompressing*
   it needs ~64 MB of RAM — instant freeze. `--lzma2=dict=2MiB` needs 2-4 MB and costs
   0.3 MB of archive size. Pick your compressor by decode-side memory, not compression ratio.

2. **A hard heap cap.** `GOGC=50` plus `GOMEMLIMIT=20MiB` turned "the heap grew to 21 MB"
   into "the heap is not allowed to exceed 20 MB". 9 MB saved.

3. **Rule economy.** One `DOMAIN-SUFFIX,cn,DIRECT` line carries the weight that naive
   configs spread over thousands of domain rules: 8450 → 1179 rules. One expressive rule
   beats a hundred literal ones.

4. **Device-side subscription update.** The router never downloads the subscription.
   The phone or laptop you tap the button on does the downloading and POSTs the body;
   the router only receives, stream-extracts with `awk` and applies. Router outbound
   traffic for updates: **zero**.

5. **procd instead of `nohup`.** Every `&`-launched process dies with its SSH session.
   Supervising through procd removed an entire class of "it worked yesterday" failures.

### What you get

- a transparent proxy for every LAN device, no client install
- unattended boot, ~60 s to ready, survives power loss
- a Chinese/English dashboard **and** a native LuCI app
- a reproducible build script and a 6-architecture CI matrix
- a bundled DHCP+TFTP recovery server, because I bricked mine twice while learning this

Everything is documented bilingually, including the **memory design** and a **9-stage
install order** — the order matters, and skipping the memory guards will freeze the
device mid-configuration.

**Repo:** https://github.com/Inceptzws/mihomo-lowmem
**License:** MIT (the deployment glue); mihomo itself is GPL-3.0.

If you have a 128 MB router in a drawer, it can do more than you think. Just count the
megabytes before you ask it to.

---

## 中文

### 在内存不够用的路由器上跑代理内核

我有一台旧的小米路由器 4A 千兆版 —— MT7621A、128MB 内存、16MB 闪存，一直躺在抽屉里。
我想让局域网里所有设备都走代理，又不想在每台设备上装客户端，于是刷了 OpenWrt，
装上了 mihomo。

结果不是"跑得慢"，而是**直接卡死**：ping 还通，网页和 SSH 全部超时，
`top` 里负载接近 10 却看不到任何占用它的用户进程 —— 内核把所有时间都花在回收内存上了。

算一下就知道为什么，简单到有点尴尬：

```
可用内存 ........................................... 47 MB
mihomo 内核解压后 .................................. 28.25 MB
运行时堆（默认参数） ............................... ~21 MB
                                                     ──────
                                                    49 MB   > 47 MB
```

于是我停止"想办法把内核变小"，换了一个问题：
**这里面哪些活，根本就不需要在路由器上干？**

换了这个问法之后，就有了 **[mihomo-lowmem](https://github.com/Inceptzws/mihomo-lowmem)** ——
一套顺着内存预算设计的部署方案。做完之后的数字：

```
可用内存 ........................................... 47 MB
内核解压后 ......................................... 28.25 MB
运行时堆（GOGC=50, GOMEMLIMIT=20MiB） ............... ~12 MB
                                                     ──────
                                                    40 MB   < 47 MB
→ 实测空闲 24-26MB，开机约 60 秒后代理可用
```

### 真正起作用的五个改动

1. **用小字典压缩。** `xz -9` 的字典是 64MiB，**解压**就要约 64MB 内存 —— 瞬间卡死。
   `--lzma2=dict=2MiB` 只需 2-4MB，代价是压缩包大 0.3MB。
   选压缩参数要看**解码端**内存，不是压缩率。

2. **给堆设硬上限。** `GOGC=50` 加 `GOMEMLIMIT=20MiB`，把"堆涨到了 21MB"
   变成"堆不允许超过 20MB"。省下 9MB。

3. **规则经济学。** 一行 `DOMAIN-SUFFIX,cn,DIRECT` 承担了常规配置里几千条域名规则的活儿：
   8450 条 → 1179 条。一条有表达力的规则胜过一百条罗列式规则。

4. **设备端更新订阅。** 路由器从不下载订阅。你点按钮的那台手机或电脑负责下载，
   把内容 POST 给路由器；路由器只做接收、`awk` 流式提取、应用。
   路由器为更新产生的对外流量：**零**。

5. **用 procd 而不是 `nohup`。** 用 `&` 启动的进程会跟着 SSH 会话一起死。
   交给 procd 托管，直接消灭了一整类"昨天还好好的"问题。

### 你能得到什么

- 所有局域网设备透明代理，无需安装客户端
- 无人值守开机，约 60 秒就绪，断电重启自动恢复
- 中英文管理面板 **以及** 原生 LuCI 应用
- 可复现的编译脚本 + 6 架构 CI 矩阵
- 自带 DHCP+TFTP 救砖服务器 —— 因为我在摸索过程中把自己的路由器刷砖了两次

所有内容都是双语文档，包括**内存设计**和**9 阶段安装顺序** ——
顺序很重要，跳过内存保护参数会把设备卡死在配置中途。

**仓库：** https://github.com/Inceptzws/mihomo-lowmem
**许可：** MIT（部署胶水代码）；mihomo 本体为 GPL-3.0。

如果你抽屉里也有一台 128MB 的路由器，它比你想的能干。只是在下命令之前，
先把那几十 MB 算清楚。

---

## Suggested platforms / 建议发布渠道

| Platform | Note |
|---|---|
| GitHub repo description + Topics | set topics: `openwrt mihomo clash-meta mt7621 low-memory ramips transparent-proxy nftables` |
| [OpenWrt Forum](https://forum.openwrt.org) | "Community Builds" or the appropriate hardware thread |
| [r/openwrt](https://reddit.com/r/openwrt) | attach the memory-budget diagram |
| Hacker News | lead with the 49 MB vs 47 MB arithmetic, not with "proxy" |
| Your own blog | link the repo and the install guide |

**Tone reminder / 语气提醒:** lead with the engineering problem. The interesting part is
the memory budget, not which protocol you tunnel. Reviewers on every one of these
platforms respond far better to measured numbers than to features.
**语气提醒**：先讲工程问题。有意思的是内存预算，不是你用哪种协议。
这些平台的读者对"实测数字"的反应，远好于对"功能列表"的反应。
