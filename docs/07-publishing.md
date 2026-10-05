# 07 · Publishing / 发布指南

## English

### A. Publish to GitHub

```sh
cd mihomo-lowmem

# 1. create an empty repo on GitHub named `mihomo-lowmem` (no README, no license)

# 2. point the local repo at it and push
git remote add origin git@github.com:<YOUR_USER>/mihomo-lowmem.git
git branch -M main
git push -u origin main
```

Replace `<YOUR_USER>` with your GitHub account. Use HTTPS instead of SSH if you
prefer: `https://github.com/<YOUR_USER>/mihomo-lowmem.git`.

**Before pushing, re-run the privacy scan:**

```sh
grep -rniE 'password|secret|token|ssid|sub(scription)?[_-]?url|[0-9a-f]{2}(:[0-9a-f]{2}){5}' \
  --include='*.sh' --include='*.py' --include='*.yaml' --include='*.md' --include='*.html' .
grep -rn 'BEGIN.*PRIVATE KEY' . 
```

Both must return nothing (or only obvious placeholders).

### B. Recommended repo settings

| Setting | Value |
|---|---|
| Description | Memory-optimized transparent proxy for constrained OpenWrt routers (MT7621A / 128 MB class) |
| Topics | `openwrt` `mihomo` `clash-meta` `mt7621` `low-memory` `ramips` `transparent-proxy` `nftables` |
| License | MIT (already included) |
| Default branch | `main` |
| Releases | attach `CrashCore.xz` + `openwrt-package/` as assets if you build binaries |

> Binary releases are optional. If you attach a prebuilt core, also attach its SHA256
> and the exact build command, so users can reproduce it.

### C. Submit to OpenWrt upstream

OpenWrt does **not** accept whole projects — it accepts **packages**. The package
definition is in `openwrt-package/`.

```sh
# 1. fork openwrt/packages on GitHub, then:
git clone https://github.com/<YOUR_USER>/packages.git
cd packages
git remote add upstream https://github.com/openwrt/packages.git

# 2. add the package following upstream layout
mkdir -p net/mihomo-lowmem/files
cp /path/to/mihomo-lowmem/openwrt-package/Makefile       net/mihomo-lowmem/
cp /path/to/mihomo-lowmem/files/start.sh                 net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/restart.sh               net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/nft.rules                net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/config.template.yaml     net/mihomo-lowmem/files/
cp /path/to/mihomo-lowmem/files/init.d/mihomo            net/mihomo-lowmem/files/mihomo.init

# 3. commit (signed off — required by OpenWrt)
git checkout -b mihomo-lowmem
git add net/mihomo-lowmem
git commit -s -m "mihomo-lowmem: add memory-optimized mihomo build

Add a variant of the mihomo package built with the with_low_memory tag and
shipped with aggressive GC defaults (GOGC=50, GOMEMLIMIT=20MiB) so it can run
on MT7621A / 128 MB class devices where ~47 MB of RAM is usable.

Measured on Xiaomi Router 4A Gigabit (R4A / DVB4218CN), OpenWrt 23.05.5:
  default build: heap ~21 MB, total demand ~49 MB -> memory exhaustion
  this variant : heap ~12 MB, total demand ~40 MB -> 24-26 MB free

Signed-off-by: Your Name <you@example.com>"

# 4. verify it builds in a real tree (reviewers expect this)
git push origin mihomo-lowmem
```

Then open a PR against `openwrt/packages`. In the PR body, include:

- **what** the variant is and **why** it exists (with the memory numbers above),
- the **build test** you ran and its result,
- confirmation that **no credentials or personal data** are included.

**Realistic expectations**

| Aspect | Reality |
|---|---|
| Review time | weeks; maintainers are volunteers |
| Likely feedback | "why not just tune the default package at runtime?" — answer with the build-tag and heap measurements |
| Alternative | keep it as a **third-party feed** — fully acceptable, no review needed |

### D. Running it as your own feed (fastest path) — ✅ already published
### D. 做成自己的 feed（最快路径）—— ✅ 已完成

**Status: published at <https://github.com/Inceptzws/openwrt-mihomo-lowmem-feed> ✓**

**状态：已发布 ✓** <https://github.com/Inceptzws/openwrt-mihomo-lowmem-feed>

If you do not want to wait for upstream, publish a feed:

```sh
# a feed is just a git repo with a `Packages` index, or a directory in src-link
echo "src-git mihomolowmem https://github.com/<YOUR_USER>/openwrt-mihomo-lowmem-feed.git" \
  >> feeds.conf.default
./scripts/feeds update mihomolowmem
./scripts/feeds install -a -p mihomolowmem
```

Document that install line in your README so users can add your feed in one step.

---

## 中文

### A. 发布到 GitHub

```sh
cd mihomo-lowmem

# 1. 在 GitHub 上创建一个空仓库 `mihomo-lowmem`（不要勾选 README 和 license）

# 2. 关联远程并推送
git remote add origin git@github.com:<你的用户名>/mihomo-lowmem.git
git branch -M main
git push -u origin main
```

把 `<你的用户名>` 换成你的 GitHub 账号。偏好 HTTPS 就用：
`https://github.com/<你的用户名>/mihomo-lowmem.git`。

**推送前务必再跑一次隐私扫描：**

```sh
grep -rniE 'password|secret|token|ssid|sub(scription)?[_-]?url|[0-9a-f]{2}(:[0-9a-f]{2}){5}' \
  --include='*.sh' --include='*.py' --include='*.yaml' --include='*.md' --include='*.html' .
grep -rn 'BEGIN.*PRIVATE KEY' .
```

两条都应当没有输出（或只有明显的占位符）。

### B. 建议的仓库设置

| 设置 | 值 |
|---|---|
| Description | Memory-optimized transparent proxy for constrained OpenWrt routers (MT7621A / 128 MB class) |
| Topics | `openwrt` `mihomo` `clash-meta` `mt7621` `low-memory` `ramips` `transparent-proxy` `nftables` |
| License | MIT（已包含）|
| 默认分支 | `main` |
| Releases | 如果编译了二进制，可把 `CrashCore.xz` 与 `openwrt-package/` 作为附件 |

> 二进制发布是可选的。如果附上预编译内核，请同时附上 SHA256 和完整的编译命令，
> 便于他人复现。

### C. 提交到 OpenWrt 上游

OpenWrt **不接受整个项目** —— 它只接受**软件包**。包定义在 `openwrt-package/`。

具体命令见上方英文部分。要点：

1. fork `openwrt/packages`，按上游目录规范把包放进 `net/mihomo-lowmem/`
2. 用 `git commit -s` 签名提交（OpenWrt 要求 Sign-off）
3. **在真实编译树里验证能编译通过**（评审会要求）
4. 开 PR，正文里说明**为什么**需要这个变体，并附上实测内存数字

**现实预期**

| 方面 | 实际情况 |
|---|---|
| 评审周期 | 数周；维护者都是志愿者 |
| 可能的反馈 | "为什么不在运行时调默认包？" —— 用编译标签和堆实测数据回答 |
| 替代方案 | 做成**第三方 feed** —— 完全可行，无需评审 |

### D. 做成自己的 feed（最快路径）

不想等上游就用这招：

```sh
echo "src-git mihomolowmem https://github.com/<你的用户名>/openwrt-mihomo-lowmem-feed.git" \
  >> feeds.conf.default
./scripts/feeds update mihomolowmem
./scripts/feeds install -a -p mihomolowmem
```

把这条安装命令写进 README，用户就能一步添加你的 feed。
