# OpenWrt package / OpenWrt 软件包

This directory contains a ready-to-submit **OpenWrt package definition**
for the memory-optimized mihomo build.

本目录包含一份可直接提交的 **OpenWrt 软件包定义**（内存优化版 mihomo）。

## Use it as a local feed / 作为本地 feed 使用

```sh
# 1. copy into your OpenWrt buildroot feed directory
#    复制到你的 OpenWrt 编译环境 feed 目录
mkdir -p openwrt/package/mihomo-lowmem
cp -r openwrt-package/* openwrt/package/mihomo-lowmem/

# 2. build
#    编译
cd openwrt
make menuconfig      # Network -> Web Servers/Proxies -> mihomo-lowmem
make package/mihomo-lowmem/compile V=s
```

## Submitting upstream / 提交到上游

OpenWrt accepts packages in two places / OpenWrt 有两个接受位置：

| Destination / 去处 | What to send / 提交什么 |
|---|---|
| [openwrt/packages](https://github.com/openwrt/packages) | a net/ package (this Makefile) / net 分类的软件包 |
| [openwrt/luci](https://github.com/openwrt/luci) | optional LuCI app (if you add a UI) / 可选的 LuCI 界面 |

See `docs/06-contributing.md` for the exact steps.
具体步骤见 `docs/06-contributing.md`。

## File layout expected by the Makefile / Makefile 依赖的文件布局

```
openwrt-package/
├── Makefile
└── files/
    ├── mihomo.init          # procd init script / procd 启动脚本
    ├── config.template.yaml # default config / 默认配置
    ├── start.sh
    ├── restart.sh
    └── nft.rules
```

The `files/` entries are expected to be symlinks or copies of the
repository's `files/` directory.
`files/` 里的内容应指向仓库的 `files/` 目录（软链接或复制均可）。
