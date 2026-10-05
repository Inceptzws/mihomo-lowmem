# 06 · Contributing & Upstream submission / 参与贡献与提交上游

## English

### Repository layout

```
mihomo-lowmem/
├── README.md                  bilingual overview
├── LICENSE                    MIT
├── build/build-mihomo.sh      reproducible core build
├── files/                     things deployed to the router
│   ├── start.sh  restart.sh   boot / restart logic
│   ├── nft.rules              transparent proxy rules
│   ├── config.template.yaml   config template (placeholders only)
│   ├── init.d/mihomo          procd service
│   └── www/cgi-bin/save-sub   subscription receiver
├── ui/index.html              dashboard (no build step)
├── recovery/tftp-recovery.py  DHCP+TFTP unbrick server
├── openwrt-package/           OpenWrt package definition
└── docs/                      this documentation
```

### Ground rules

1. **No credentials, ever.** No subscription URLs, node names, SSIDs, passwords,
   device IDs or MAC addresses — not in code, not in comments, not in tests.
   Run the privacy scan before every push:
   ```sh
   grep -rniE 'password|secret|token|sub.*url|ssid|[0-9a-f]{2}(:[0-9a-f]{2}){5}' \
     --include='*.sh' --include='*.py' --include='*.yaml' --include='*.html' .
   ```
2. **Every script must be POSIX-sh compatible** unless it targets a specific
   interpreter (the router's shell is busybox `ash`).
3. **Every new memory-hungry feature needs a budget statement** — what it costs at
   peak and at rest. PRs that raise the floor without saying so will be asked for one.
4. **Test on real hardware** if at all possible. Emulators do not reproduce the
   memory pressure that this project exists to solve.

### Local development loop

```sh
# build the core
cd build && ./build-mihomo.sh

# push to a test router
ROUTER=192.168.1.1
scp CrashCore.xz                       root@$ROUTER:/overlay/mihomo/CrashCore.xz
scp -r files/* ui docs                 root@$ROUTER:/tmp/deploy/
ssh root@$ROUTER 'sh /overlay/mihomo/start.sh && free'
```

Always confirm `free` before and after your change, and note both numbers in the PR.

### Submitting to OpenWrt upstream

OpenWrt takes packages through Gerrit/GitHub pull requests against these repositories:

| Repo | What goes there |
|---|---|
| [openwrt/packages](https://github.com/openwrt/packages) | the package itself — `net/mihomo-lowmem/Makefile` + `files/` |
| [openwrt/luci](https://github.com/openwrt/luci) | an optional LuCI front-end |
| [openwrt/openwrt](https://github.com/openwrt/openwrt) | only kernel/target changes |

**Step by step**

```sh
# 1. fork and clone
git clone https://github.com/<you>/packages.git
cd packages

# 2. create the package directory, matching upstream structure
mkdir -p net/mihomo-lowmem/files
cp /path/to/mihomo-lowmem/openwrt-package/Makefile   net/mihomo-lowmem/
cp /path/to/mihomo-lowmem/files/start.sh             net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/restart.sh           net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/nft.rules            net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/config.template.yaml net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/init.d/mihomo        net/mihomo-lowmem/files/mihomo.init

# 3. style: one commit per logical change, sign off
git checkout -b mihomo-lowmem
git add net/mihomo-lowmem
git commit -s -m "mihomo-lowmem: add memory-optimized mihomo core"

# 4. verify it actually builds in a real tree
#    (a build test is expected in review)
cd /path/to/openwrt
ln -s /path/to/packages net/mihomo-lowmem
make defconfig
make package/mihomo-lowmem/compile V=s

# 5. push and open a PR
git push origin mihomo-lowmem
```

**Review checklist that maintainers will apply**

- [ ] builds cleanly on the current `openwrt/packages` HEAD
- [ ] `PKG_MIRROR_HASH` / `PKG_HASH` present (not `skip`) in the submitted version
- [ ] install section creates no files outside the package's own paths
- [ ] init script is procd-based and passes shellcheck
- [ ] no network access at build time beyond declared sources
- [ ] license of the packaged software is declared (`GPL-3.0` for mihomo)
- [ ] description is factual and mentions the memory-optimized build tag

> Tip: mention in the PR body *why* the variant exists (the `with_low_memory` tag and
> the measured RAM figures). Distro maintainers accept variants far more readily when
> the motivation is quantitative.

### Reporting issues

Include:

```
- router model, SoC, RAM size
- OpenWrt version and target
- output of: free -m ; /etc/init.d/mihomo status ; logread | tail -50
- the config's rule count and proxy count (never the actual content)
```

---

## 中文

### 仓库结构

见上方英文部分的目录树。

### 基本规则

1. **绝不提交凭据。** 订阅地址、节点名称、WiFi 名、密码、设备 ID、MAC 地址 ——
   代码里、注释里、测试里都不行。每次推送前跑一遍隐私扫描：
   ```sh
   grep -rniE 'password|secret|token|sub.*url|ssid|[0-9a-f]{2}(:[0-9a-f]{2}){5}' \
     --include='*.sh' --include='*.py' --include='*.yaml' --include='*.html' .
   ```
2. **脚本要兼容 POSIX sh**，除非明确针对特定解释器（路由器的 shell 是 busybox `ash`）。
3. **任何吃内存的新功能都要附"预算说明"** —— 峰值多少、常态多少。
   不说明就抬高内存底线的 PR 会被要求补上。
4. **尽量在真机测试**。模拟器无法复现本项目要解决的那种内存压力。

### 本地开发循环

```sh
cd build && ./build-mihomo.sh

ROUTER=192.168.1.1
scp CrashCore.xz     root@$ROUTER:/overlay/mihomo/CrashCore.xz
scp -r files/* ui    root@$ROUTER:/tmp/deploy/
ssh root@$ROUTER 'sh /overlay/mihomo/start.sh && free'
```

改动前后都要看 `free`，并把两个数字写进 PR。

### 提交到 OpenWrt 上游

OpenWrt 通过以下仓库的 PR 接收软件包：

| 仓库 | 放什么 |
|---|---|
| [openwrt/packages](https://github.com/openwrt/packages) | 软件包本体 —— `net/mihomo-lowmem/Makefile` + `files/` |
| [openwrt/luci](https://github.com/openwrt/luci) | 可选的 LuCI 界面 |
| [openwrt/openwrt](https://github.com/openwrt/openwrt) | 仅内核/目标平台改动 |

**具体步骤**（命令见上方英文部分）

简要说明：
1. fork 并克隆 `openwrt/packages`
2. 按上游目录规范建立 `net/mihomo-lowmem/`，放入 Makefile 与 `files/`
3. 一个逻辑改动一个提交，使用 `git commit -s` 签名
4. **在真实编译树里验证能编译通过**（评审会要求）
5. 推送并开 PR

**维护者会检查的清单**

- [ ] 能在当前 `openwrt/packages` HEAD 上干净编译
- [ ] 提交版本里 `PKG_MIRROR_HASH` / `PKG_HASH` 已填写（不是 `skip`）
- [ ] install 段不往包自己路径之外写文件
- [ ] init 脚本基于 procd 且通过 shellcheck
- [ ] 构建期除声明的源之外不访问网络
- [ ] 声明了被封装软件的许可证（mihomo 为 `GPL-3.0`）
- [ ] 描述文字实事求是，并提到内存优化编译标签

> 小提示：在 PR 正文里说明**为什么**需要这个变体（`with_low_memory` 标签、
> 以及实测的内存数字）。动机一旦量化，发行版维护者接受变体会容易得多。

### 提交 issue 时请附上

```
- 路由器型号、SoC、内存大小
- OpenWrt 版本与 target
- 以下命令的输出：free -m ; /etc/init.d/mihomo status ; logread | tail -50
- 配置的规则条数与线路条数（不要贴实际内容）
```
