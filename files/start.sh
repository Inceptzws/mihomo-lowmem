#!/bin/sh
#
# mihomo-lowmem :: boot-time launcher
# 内存受限路由器的 mihomo 启动脚本
#
# Design notes / 设计说明:
#   - The 28 MB binary lives compressed on flash (5.9 MB xz) and is
#     decompressed into RAM (tmpfs) on every boot.
#     28MB 内核以 5.9MB 压缩包存于闪存，每次开机解压到内存盘。
#   - Decompression MUST use a small LZMA2 dictionary (2 MiB), because
#     the default xz -9 dictionary is 64 MiB and will exhaust RAM.
#     解压必须用小字典（2MiB），xz -9 的 64MiB 字典会耗尽内存。
#   - The heap is hard-capped via GOGC / GOMEMLIMIT.
#     堆内存通过 GOGC / GOMEMLIMIT 硬限制。
#
BASE=/overlay/mihomo
WORK=/tmp/mihomo
MIN_FREE_KB=35000          # need >= 35 MB free in tmpfs / tmpfs 至少 35MB
MIN_CORE_BYTES=28000000    # sanity threshold / 完整性阈值

mkdir -p "$WORK/providers" "$WORK/ui"

# 1) Pre-flight: enough scratch space? / 预检：临时空间是否充足
FREE=$(df -k /tmp | awk 'NR==2{print $4}')
[ "${FREE:-0}" -lt "$MIN_FREE_KB" ] && {
    echo "not enough tmpfs space (${FREE}KB)" > /tmp/mihomo-status
    exit 1
}

# 2) Decompress the core into RAM / 解压内核到内存盘
rm -f "$WORK/CrashCore"
xz -d -c "$BASE/CrashCore.xz" > "$WORK/CrashCore" 2>/dev/null

# 3) Verify integrity before running (a truncated core would crash) 
#    启动前校验完整性（截断的内核会崩溃）
SIZE=$(wc -c < "$WORK/CrashCore" 2>/dev/null)
[ -z "$SIZE" ] && SIZE=0
[ "$SIZE" -lt "$MIN_CORE_BYTES" ] && {
    echo "incomplete decompression (${SIZE}B)" > /tmp/mihomo-status
    rm -f "$WORK/CrashCore"
    exit 1
}
chmod 755 "$WORK/CrashCore"

# 4) Stage config + dashboard in RAM / 把配置和面板放到内存盘
cp -f "$BASE/config.yaml" "$WORK/config.yaml"
cp -rf "$BASE/ui/." "$WORK/ui/" 2>/dev/null

# 5) Launch through procd if available, otherwise fall back to a plain fork
#    优先用 procd 托管（崩溃自动重启），否则退化为普通 fork
if [ -x /etc/init.d/mihomo ]; then
    /etc/init.d/mihomo restart
else
    pkill -9 CrashCore 2>/dev/null
    sleep 1
    cd "$WORK"
    GOGC=50 GOMEMLIMIT=20MiB "$WORK/CrashCore" -d "$WORK" > /tmp/clash.log 2>&1 &
    sleep 10
    netstat -tln 2>/dev/null | grep -q ':7890' && echo OK > /tmp/mihomo-status \
                                              || echo FAIL > /tmp/mihomo-status
fi

# 6) Transparent-proxy rules last (never block boot if they fail)
#    最后加载透明代理规则（失败也不能卡住启动）
nft list table ip mihomo >/dev/null 2>&1 || nft -f "$BASE/nft.rules"
exit 0
