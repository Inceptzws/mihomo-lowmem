#!/bin/bash
#
# mihomo-lowmem :: build script
# 自编译精简内核 / Build a stripped-down mihomo core
#
# WHY BUILD IT YOURSELF? / 为什么要自己编译？
#   The upstream release binary is ~30+ MB because it bundles optional
#   features (gvisor netstack, every protocol, ...). On a router with
#   47 MB of usable RAM, every megabyte of text pages matters.
#   官方发布版约 30+ MB，因为它打包了 gvisor 等可选特性。
#   在只有 47MB 可用内存的路由器上，每一 MB 都很关键。
#
# RESULT / 效果:  30+ MB  ->  28.25 MB
#
set -e

MIHOMO_VERSION="${MIHOMO_VERSION:-v1.18.0}"
TARGET_ARCH="mipsle"          # mipsel_24kc (MT7621A) / 软浮点
OUT="mihomo-new"

echo "==> 1. fetch source / 拉取源码"
[ -d mihomo ] || git clone --depth 1 --branch "$MIHOMO_VERSION" \
    https://github.com/MetaCubeX/mihomo.git

cd mihomo

echo "==> 2. build / 编译"
GOOS=linux GOARCH=mipsle GOMIPS=softfloat \
CGO_ENABLED=0 \
go build -trimpath \
    -tags "with_low_memory" \
    -ldflags "-s -w -X github.com/metacubex/mihomo/constant.Version=${MIHOMO_VERSION}" \
    -o "../${OUT}" .

cd ..

echo "==> 3. strip / 去符号"
mips-linux-gnu-strip "$OUT" 2>/dev/null || echo "   (install mips-linux-gnu-binutils to strip further)"

echo "==> 4. compress with a SMALL dictionary / 用小字典压缩"
#  ★ CRITICAL ★  xz default (-9) uses a 64 MiB dictionary.
#  Decompressing then requires ~64 MB of RAM -> router freezes.
#  A 2 MiB dictionary needs only 2-4 MB to decompress.
#  ★ 关键 ★  xz 默认 -9 使用 64MiB 字典，解压需要约 64MB 内存，路由器会卡死。
#  2MiB 字典解压只需 2-4MB。
xz -6 --lzma2=dict=2MiB -c "$OUT" > CrashCore.xz

echo
echo "==> done / 完成"
ls -la "$OUT" CrashCore.xz | awk '{printf "    %-16s %8.2f MB\n", $9, $5/1048576}'
cat <<'NOTE'

  Deploy / 部署:
    scp mihomo-new      root@ROUTER:/tmp/       # for a one-off test / 单次测试
    scp CrashCore.xz    root@ROUTER:/overlay/mihomo/CrashCore.xz

  Verify before trusting it / 使用前先验证:
    xz -d -c CrashCore.xz | wc -c      # 应为 28250000 左右 / should be ~28.25 MB

  Build tags explained / 编译标签说明:
    with_low_memory  -> aggressive GC defaults, smaller caches / 更激进的 GC、更小的缓存
    -s -w            -> strip symbols, smaller binary      / 去掉符号表，体积更小
    (gvisor omitted) -> saves several MB, not needed for a router / 省几 MB，路由器用不到
NOTE
