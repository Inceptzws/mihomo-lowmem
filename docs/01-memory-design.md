# 01 · Memory Design ★ / 内存优化设计 ★

> This is the heart of the project. Everything else is plumbing.
> 这是本项目的核心，其余都是配套设施。

---

## English

### 0. The design principle

> **Move every heavy job off the router.**

The router has a hard 47 MB budget. Instead of trying to make heavy work cheaper,
we ask: *can a different device do this instead?*

| Job | Naive location | This project | Why |
|---|---|---|---|
| Storing the 28 MB core | router flash (8 MB) — impossible | compressed on flash + RAM at boot | flash is smaller than the core |
| Decompressing the core | router CPU with a 64 MiB dictionary — freezes | 2 MiB dictionary | decompression cost is the *dictionary* |
| Holding the runtime heap | unbounded → 21 MB | `GOGC=50` + `GOMEMLIMIT=20MiB` → ~12 MB | hard cap beats hope |
| Matching traffic to rules | 8450 hand-written rules | 1179 rules, TLD-driven | one rule can carry a whole TLD |
| Downloading the subscription | **router** (needs TLS, buffers, parsing) | **the device that taps the button** | phone has 100× the RAM |
| Parsing the subscription | read whole file into memory | stream with `awk` | peak memory should be O(1) |

### 1. Store compressed on flash, decompress into RAM

```
PROBLEM   The decompressed core is 28.25 MB.
          Writable flash (/overlay) is only 8.3 MB. It does not fit.
          Writing it there fills the filesystem and corrupts JFFS2.

DESIGN    flash  (persistent) → CrashCore.xz           5.91 MB
          tmpfs  (volatile)   → CrashCore              28.25 MB

BOOT      1. check tmpfs free space (abort if < 35 MB)  ← prevents truncated files
          2. xz -d into tmpfs
          3. verify size >= 28,000,000 bytes            ← a truncated core would crash
          4. exec
```

**Why the space check first?** Because `xz -d` into a full filesystem silently
produces a truncated binary. Without the check you get a core that starts and then
dies in confusing ways — this exact failure mode cost hours during development.

### 2. Compression dictionary: 64 MiB → 2 MiB ★ the trap

```
xz -9  (default)      dictionary = 64 MiB  → decompression needs ~64 MB RAM
                                            → router freezes instantly ✗

xz -6 --lzma2=dict=2MiB   dictionary = 2 MiB → decompression needs 2-4 MB ✓
```

Trade-off: the archive grows from 5.59 MB to 5.91 MB (**+0.3 MB**), while
decompression memory drops by **94 %**.

> **Rule of thumb:** for embedded targets, pick the compressor by its *decode-side*
> memory requirement, not by its compression ratio.

Verification: the decompressed output is byte-identical (MD5 match) — always check.

### 3. Hard-cap the runtime heap

```
PROBLEM   Go's GC is lazy by default. The heap grew to ~21 MB in practice,
          which pushed total demand to 49 MB -> freeze.

DESIGN    GOGC=50               trigger GC at half the default threshold
          GOMEMLIMIT=20MiB      absolute ceiling the runtime will not exceed
```

```
heap  21 MB -> ~12 MB        (saves 9 MB)
total 49 MB -> 40 MB         (7 MB headroom)
```

`GOMEMLIMIT` is the important one: it converts "we hope the heap stays small" into
"the runtime is not allowed to exceed this".

### 4. Rule economy: let the TLD do the work ★

```
PROBLEM   Traffic classification is rule-driven. Naive configurations enumerate
          every known domain: 8450 rules and still growing.
          Every rule costs memory, and matching costs CPU.

DESIGN    One suffix rule covers an entire top-level domain:

              DOMAIN-SUFFIX,cn,DIRECT

          A single line decides the path for effectively all .cn domains.
          Then add:
            · ~140 curated service domains   (explicit, high-traffic)
            · ~1030 targeted proxy rules
            · 1 catch-all rule
```

**Why this is the right move:**

| | naive enumeration | TLD-driven |
|---|---|---|
| rules | 8450 | **1179** (−86 %) |
| config size | very large | **92 KB** |
| matching | linear over thousands | short suffix compare |
| maintenance | add a rule per domain | add nothing for `.cn` |

> **Design philosophy:** trade *expressiveness per rule* for memory and CPU.
> One well-chosen rule beats a hundred literal ones.

### 5. Device-side subscription update ★

```
NAIVE     The router downloads the subscription.
          Requires: TLS handshake + multi-hundred-KB buffering + format parsing
          + retries. The subscription host is frequently unreachable directly,
          so it also has to route through its own proxy first.
          MEASURED: the core retried in a loop, RAM filled, SSH stopped answering.

DESIGN    The device you tap the button on does the download.

            phone/laptop
              │  ① fetch the subscription over its OWN network
              │     (it is already behind the router, so it is proxied correctly)
              ↓
            router
              │  ② receive the body (POST)
              │  ③ stream-extract only the needed section
              │  ④ rebuild config.yaml, restart the core  (~10 s)
              ↓
            done

          The router only ever does: receive → extract → apply.
          It never opens an outbound connection for this.
```

**Implementation notes**

- Endpoint: `POST /cgi-bin/save-sub` (uhttpd CGI), CORS-enabled so the dashboard
  can call it from any device.
- It refuses bodies yielding fewer than 3 proxies — never install a broken config.
- Because it is stateless, it works identically from a phone, tablet, laptop or TV.

| | naive (router-side) | device-side |
|---|---|---|
| router outbound TLS | yes | **no** |
| router peak memory | high, spikes | **~O(1)** |
| fails when host is blocked | yes | **no** |
| works from any device | n/a | **yes** |

### 6. Streaming config processing

```
PROBLEM   The subscription endpoint returns a full config for browser user agents
          (measured: 517 KB). The core needs only the proxy list.
          Reading it fully means peak memory ≈ file size.

DESIGN    awk, line by line:
              emit from `proxies:` until the next top-level key

MEASURED  517 KB full config  ->  25 KB / 70 clean proxies
          peak memory: essentially unchanged
```

The same trick is used when rebuilding `config.yaml`:
`head.txt` + streamed proxies + `tail.txt` → the file is never held in memory.

### 7. Compile a slimmer core

```
upstream release          30+ MB     (bundles gvisor, all protocols, symbols)
this project              28.25 MB   (with_low_memory, no gvisor, stripped)
```

Tags and flags used:

| flag | effect |
|---|---|
| `with_low_memory` | smaller internal caches, GC tuned for constrained devices |
| `-ldflags "-s -w"` | strip symbol table and DWARF |
| no `with_gvisor` | several MB saved; not needed for a router |
| (hysteria2 removed from config) | its QUIC stack panicked the core on this SoC |

### 8. Supervise with procd

```
PROBLEM   Starting with nohup/& under SSH means the process receives SIGHUP
          when the session closes and silently disappears.

DESIGN    /etc/init.d/mihomo (procd)
            respawn 3600 5 5   auto-restart on crash
            boot enabled       auto-start
            no session tie     survives logout
```

Costs nothing at runtime and removes an entire class of "it worked yesterday" bugs.

### 9. The complete ledger

| Stage | Naive | This project | Improvement |
|---|---|---|---|
| core storage | 28 MB on flash — **does not fit** | 5.91 MB archive | flash use −79 % |
| core decompression | 64 MiB dictionary — **freezes** | 2 MiB dictionary | peak RAM −94 % |
| runtime heap | ~21 MB | ~12 MB | −9 MB |
| traffic rules | 8450 | 1179 | −86 % |
| subscription fetch | router-side | **device-side** | router cost −100 % |
| config parsing | full read | **streaming** | O(1) |
| core binary | 30+ MB | 28.25 MB | −6 % |
| process supervision | orphaned | procd | reliability ↑↑ |

```
BEFORE   49 MB needed  >  47 MB available    ✗ guaranteed freeze
AFTER    40 MB needed  <  47 MB available    ✓ 24-26 MB measured free
```

---

## 中文

### 0. 设计原则

> **把每一项"重活"都从路由器上挪走。**

路由器只有 47MB 的硬预算。我们不去想办法让重活变便宜，而是问：
*这件事能不能换一台设备来做？*

| 任务 | 常规做法 | 本项目 | 原因 |
|---|---|---|---|
| 存放 28MB 内核 | 放路由器闪存（只有 8MB）——不可能 | 压缩存闪存 + 开机解压到内存 | 闪存比内核还小 |
| 解压内核 | 用 64MiB 字典在路由器上解压——卡死 | 改用 2MiB 字典 | 解压成本取决于字典 |
| 运行时堆 | 不限制 → 涨到 21MB | `GOGC=50` + `GOMEMLIMIT=20MiB` → 约 12MB | 硬上限胜过"但愿" |
| 规则匹配 | 8450 条手写规则 | 1179 条，由顶级域承担 | 一条规则可承载整个顶级域 |
| 下载订阅 | **路由器**下载（要 TLS、缓冲、解析）| **点按钮的那台设备**下载 | 手机内存是路由器的百倍 |
| 解析订阅 | 整个文件读进内存 | 用 `awk` 流式处理 | 峰值内存应为 O(1) |

### 1. 压缩存闪存，解压到内存

```
问题   内核解压后 28.25MB，而可写闪存（/overlay）只有 8.3MB，装不下。
       硬写进去会填满文件系统并损坏 JFFS2。

设计   闪存（持久）→ CrashCore.xz     5.91 MB
       内存盘（易失）→ CrashCore      28.25 MB

启动   1. 先检查内存盘剩余空间（<35MB 直接放弃）← 防止解压出不完整文件
       2. xz 解压到内存盘
       3. 校验大小 ≥ 28,000,000 字节        ← 截断的内核会崩溃
       4. 启动
```

**为什么必须先查空间？** 因为写满文件系统时 `xz -d` 会**静默**产出截断的二进制。
没有这道检查，你会得到一个"能启动然后以奇怪方式死掉"的内核 ——
开发过程中正是这个失败模式浪费了好几个小时。

### 2. 压缩字典：64MiB → 2MiB ★最容易踩的坑

```
xz -9（默认）              字典 = 64MiB → 解压需要约 64MB 内存 → 路由器瞬间卡死 ✗
xz -6 --lzma2=dict=2MiB    字典 = 2MiB  → 解压只需 2-4MB            ✓
```

代价：压缩包从 5.59MB 变成 5.91MB（**只大 0.3MB**），
收益：解压内存需求下降 **94%**。

> **经验法则**：嵌入式目标要按**解码端**的内存需求选压缩参数，
> 而不是按压缩率。

验证：解压结果必须逐字节一致（MD5 相同）—— 这一步务必做。

### 3. 运行时堆硬限制

```
问题   Go 的 GC 默认很懒。实测堆会涨到约 21MB，
       加上内核后总需求 49MB → 卡死。

设计   GOGC=50             把 GC 触发阈值降到默认的一半
       GOMEMLIMIT=20MiB    运行时的绝对上限
```

```
堆      21MB → 约 12MB    （省 9MB）
总需求  49MB → 40MB       （余量 7MB）
```

`GOMEMLIMIT` 是关键：它把"希望堆别太大"变成"运行时**不允许**超过这个值"。

### 4. 规则经济学：让顶级域承担工作 ★

```
问题   分流是规则驱动的。常规配置把每个已知域名都列出来：8450 条还在增长。
       每条规则都占内存，匹配还耗 CPU。

设计   一条后缀规则覆盖整个顶级域：

           DOMAIN-SUFFIX,cn,DIRECT

       一行即可决定几乎所有 .cn 域名的走向。再补充：
         · 约 140 条精选服务域名（明确列出高频项）
         · 约 1030 条定向代理规则
         · 1 条兜底规则
```

**为什么这样做是对的：**

| | 逐条枚举 | 顶级域驱动 |
|---|---|---|
| 规则数 | 8450 | **1179**（−86%）|
| 配置大小 | 很大 | **92 KB** |
| 匹配 | 线性遍历数千条 | 短后缀比较 |
| 维护 | 每个域名加一条 | `.cn` 无需任何新增 |

> **设计哲学**：用**单条规则的表达力**换取内存和 CPU。
> 一条精选规则胜过一百条罗列式规则。

### 5. 设备端更新订阅 ★

```
常规做法  路由器自己下载订阅。
          需要：TLS 握手 + 数百 KB 缓冲 + 格式解析 + 失败重试。
          而订阅源往往无法从路由器直连，还得先绕自己的代理。
          实测结果：内核反复重试 → 内存吃满 → SSH 都不响应 ✗

本方案    由你点击按钮的那台设备负责下载。

            手机 / 电脑
              │  ① 用【它自己的网络】拉取订阅
              │     （它已经在路由器后面，所以自动走了正确的线路）
              ↓
            路由器
              │  ② 接收内容（POST）
              │  ③ 流式提取需要的部分
              │  ④ 重建 config.yaml 并重启内核（约 10 秒）
              ↓
            完成

          路由器全程只做：接收 → 提取 → 应用。
          它不会为这件事发起任何对外连接。
```

**实现要点**

- 接口：`POST /cgi-bin/save-sub`（uhttpd CGI），开启 CORS，
  使面板可以从任意设备调用。
- 提取到的线路少于 3 条时直接拒绝 —— **绝不写入坏配置**。
- 无状态，因此手机、平板、电脑、电视操作完全一致。

| | 常规（路由器侧）| 设备端 |
|---|---|---|
| 路由器对外 TLS | 有 | **无** |
| 路由器峰值内存 | 高、有尖峰 | **约 O(1)** |
| 订阅源被墙时 | 失败 | **不受影响** |
| 任意设备可操作 | — | **是** |

### 6. 流式配置处理

```
问题   订阅源对浏览器返回的是完整配置文件（实测 517KB），
       而内核只需要其中的线路列表。
       整体读入内存 → 峰值内存 ≈ 文件大小。

设计   用 awk 逐行处理：
         从 `proxies:` 开始输出，遇到下一个顶级键就停止

实测   517KB 完整配置 → 25KB / 70 条干净线路
       峰值内存：几乎无增长
```

重建 `config.yaml` 时用的是同一招：
`head.txt` + 流式线路 + `tail.txt` → 全程不把文件装进内存。

### 7. 编译更瘦的内核

```
官方发布版        30+ MB   （打包了 gvisor、所有协议、符号表）
本项目            28.25 MB （with_low_memory、无 gvisor、已去符号）
```

使用的标签与参数：

| 参数 | 作用 |
|---|---|
| `with_low_memory` | 更小的内部缓存，GC 面向受限设备调优 |
| `-ldflags "-s -w"` | 去掉符号表和调试信息 |
| 不用 `with_gvisor` | 省几 MB，路由器用不到 |
| （配置中移除 hysteria2）| 它的 QUIC 栈在这个 SoC 上会导致内核 panic |

### 8. 用 procd 守护

```
问题   用 nohup/& 在 SSH 里启动，会话一断进程收到 SIGHUP 就静默消失。

设计   /etc/init.d/mihomo（procd）
         respawn 3600 5 5   崩溃自动重启
         boot enabled       开机自启
         不绑定会话          登出也不受影响
```

运行时不占额外资源，却能消除一整类"昨天还好好的"问题。

### 9. 完整账本

| 环节 | 常规做法 | 本项目 | 改善 |
|---|---|---|---|
| 内核存储 | 28MB 放闪存 ——**装不下** | 5.91MB 压缩包 | 闪存占用 −79% |
| 内核解压 | 64MiB 字典 ——**卡死** | 2MiB 字典 | 峰值内存 −94% |
| 运行时堆 | 约 21MB | 约 12MB | −9MB |
| 分流规则 | 8450 条 | 1179 条 | −86% |
| 订阅获取 | 路由器侧 | **设备侧** | 路由器成本 −100% |
| 配置解析 | 全量读入 | **流式** | O(1) |
| 内核体积 | 30+ MB | 28.25MB | −6% |
| 进程管理 | 孤儿进程 | procd | 稳定性 ↑↑ |

```
优化前   需求 49MB > 可用 47MB    ✗ 必然卡死
优化后   需求 40MB < 可用 47MB    ✓ 实测空闲 24-26MB
```
