# 05 · FAQ / 常见问题

## English

**Q: Why not just use the upstream mihomo release binary?**
Because it is ~30+ MB with optional features (gvisor, every protocol) that a router
never uses. On a 47 MB budget every megabyte of text matters.
See [01-memory-design.md](01-memory-design.md) §7.

**Q: Why not OpenClash / other Clash GUIs?**
They are excellent on routers with 256 MB+. On a 128 MB device the GUI alone plus
dependencies routinely exceeds the budget. This project deliberately has **no GUI
framework** — just a small static HTML dashboard and a REST API.

**Q: Why nftables and not iptables?**
OpenWrt 21.02+ ships nftables natively (`fw4`). Using it avoids the iptables compat
layer and its extra rules — less RAM, atomic table loads.

**Q: Why is the core decompressed on every boot instead of kept uncompressed?**
Because it does not fit: the decompressed core is 28.25 MB and writable flash is only
~8 MB. Writing it there fills the filesystem and corrupts JFFS2.
`xz -d` of a 5.9 MB archive takes a few seconds on this class of CPU.

**Q: The subscription works on my phone but the router cannot fetch it. Why?**
That is expected and is exactly why the fetch happens on the device, not the router.
The endpoint is often unreachable from the router's network position, and even when it
is reachable the TLS + buffering + parsing cost is RAM the router cannot spare.
See [01-memory-design.md](01-memory-design.md) §5.

**Q: Can I keep the router-side subscription fetch anyway?**
You can, but you are re-introducing the failure mode this project exists to avoid.
If you must, set a very long `interval` so it does not repeat, and watch `free`.

**Q: How many proxies can I load?**
Not a fixed number — what matters is free RAM after start. Guideline: stay above
**15 MB free**, and prefer keeping the rule set small (the rule set costs more than
the proxy list).

**Q: Will this work on a 256 MB router?**
Yes, and it will be comfortable. You can raise `GOMEMLIMIT`, skip the streaming
tricks, and use the upstream binary.

**Q: Do I need to recompile for a different architecture?**
Yes. Set `GOARCH`/`GOMIPS` in `build/build-mihomo.sh` for your target
(`mipsle` softfloat for MT7621A, `arm64` for many modern SoCs, etc.).

**Q: Is my traffic sent anywhere besides my proxy provider?**
No. There is no telemetry, no analytics and no external service. The dashboard and
API bind to the LAN. The only outbound traffic is what your rules send to your proxy.

**Q: What if I brick the device?**
See the recovery path in [03-installation.md](03-installation.md) and
[04-troubleshooting.md](04-troubleshooting.md). Keep `mtd` backups and ideally a
USB-TTL adapter.

---

## 中文

**问：为什么不直接用官方发布的 mihomo 二进制？**
因为它约 30+ MB，打包了路由器根本用不到的可选特性（gvisor、所有协议）。
在 47MB 的预算下，每一 MB 都算数。
见 [01-memory-design.md](01-memory-design.md) 第 7 节。

**问：为什么不用 OpenClash 之类带图形界面的方案？**
它们在 256MB 以上的路由器上非常好。但在 128MB 设备上，光界面加依赖就常常超出预算。
本项目**刻意不做 GUI 框架** —— 只有一个很小的静态 HTML 面板和一个 REST API。

**问：为什么用 nftables 而不是 iptables？**
OpenWrt 21.02+ 原生使用 nftables（`fw4`）。用它就不需要 iptables 兼容层及其额外规则 ——
更省内存，且规则表可以原子加载。

**问：为什么每次开机都要解压内核，不直接放解压后的？**
因为放不下：解压后 28.25MB，而可写闪存只有约 8MB。
硬写进去会填满文件系统并损坏 JFFS2。
在这类 CPU 上解压 5.9MB 压缩包只需几秒。

**问：订阅在我手机上能用，但路由器拉不到，正常吗？**
正常 —— 这正是"由设备拉取"的原因。
订阅源往往从路由器所处的网络位置不可达；即便可达，TLS + 缓冲 + 解析的开销
也是路由器负担不起的内存。见 [01-memory-design.md](01-memory-design.md) 第 5 节。

**问：我还是想让路由器自己拉订阅可以吗？**
可以，但你就把本项目要避开的失败模式又请回来了。
如果一定要，请把 `interval` 设得很长以免反复重试，并盯住 `free`。

**问：最多能加载多少条线路？**
没有固定数字 —— 关键是启动后的空闲内存。经验值：保持 **15MB 以上空闲**，
并且优先控制规则集大小（规则集比线路列表更吃内存）。

**问：256MB 内存的路由器能用吗？**
能，而且会很宽裕。你可以调高 `GOMEMLIMIT`、跳过流式处理技巧，直接用官方二进制。

**问：换别的架构需要重新编译吗？**
需要。在 `build/build-mihomo.sh` 里为你的目标设置 `GOARCH`/`GOMIPS`
（MT7621A 用 `mipsle` 软浮点，许多现代 SoC 用 `arm64` 等）。

**问：除了我的代理服务商，流量还会发到别处吗？**
不会。没有遥测、没有统计、没有外部服务。面板和 API 只监听局域网。
唯一的对外流量就是你的规则发往代理的那些。

**问：刷坏了怎么办？**
见 [03-installation.md](03-installation.md) 的救砖路线和
[04-troubleshooting.md](04-troubleshooting.md)。
请保留 `mtd` 分区备份，最好再备一根 USB-TTL 串口线。
