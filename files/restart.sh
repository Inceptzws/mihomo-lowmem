#!/bin/sh
# mihomo-lowmem :: lightweight restart
# 轻量重启：内核已在 RAM 中，不重新解压
# Lightweight restart: the core is already in RAM, so we skip decompression.
pkill -9 CrashCore 2>/dev/null
sleep 1
cd /tmp/mihomo
GOGC=50 GOMEMLIMIT=20MiB /tmp/CrashCore -d /tmp/mihomo > /tmp/clash.log 2>&1 &
sleep 8
nft list table ip mihomo >/dev/null 2>&1 || nft -f /overlay/mihomo/nft.rules
echo OK > /tmp/mihomo-status
