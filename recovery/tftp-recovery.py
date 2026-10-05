#!/usr/bin/env python3
"""
TFTP / DHCP recovery server for bricked Xiaomi routers
小米路由器变砖恢复服务器（DHCP + TFTP）

WHY THIS EXISTS / 为什么需要它：
  The U-Boot recovery mode of many Xiaomi routers only accepts the
  *stock* ROM over TFTP, and it broadcasts DHCP DISCOVERs on the LAN
  port. A stock tftp/dnsmasq setup usually does not answer correctly,
  so this script implements both sides with the exact quirks needed.

  许多小米路由器的 U-Boot 恢复模式只接受【原厂固件】的 TFTP 刷写，
  并且会在 LAN 口广播 DHCP 请求。普通的 tftp/dnsmasq 往往应答不正确，
  所以这里自己实现了 DHCP + TFTP 两端，并处理了各种坑。

IMPORTANT MACOS QUIRKS / 重要 macOS 坑：
  1. Without IP_BOUND_IF the DHCP reply is routed out of the Wi-Fi
     interface instead of the USB Ethernet one, so the router never
     sees it. This script sets socket option 25 (IP_BOUND_IF).
     不设置 IP_BOUND_IF 时，DHCP 应答会从 Wi-Fi 网卡发出去而不是
     USB 网卡，路由器收不到。本脚本设置了 socket 选项 25。

  2. The interface must NOT also hold a 169.254.x.x link-local address,
     otherwise replies get lost. Set a static IP and remove the
     link-local one before running.
     网卡上不能同时存在 169.254 开头的地址，否则应答会丢失。
     运行前请设置静态 IP 并清除 link-local 地址。

USAGE / 用法：
    sudo python3 tftp-recovery.py <firmware.bin> <interface>
    sudo python3 tftp-recovery.py stock-rom.bin en14

ROUTER SIDE / 路由器侧操作：
    1. unplug power, hold Reset, plug power back in and keep holding
       8-10 s until the LED blinks fast
    2. release, and this server will answer DHCP + serve the firmware

    1. 拔电源 → 按住 Reset → 插电源 → 继续按 8-10 秒直到灯快速闪烁
    2. 松手，本服务器会自动应答 DHCP 并传输固件

NOTE / 注意：
  After the transfer DO NOT cut power. Wait 10-15 minutes for the
  bootloader to finish writing and reboot by itself.
  传输完成后【不要断电】，等待 10-15 分钟让引导程序写完并自行重启。
"""
# -*- coding: utf-8 -*-
"""
小米路由器 4A 千兆版 —— 恢复模式（TFTP）救援服务器
=====================================================
作用：让 Mac 扮演小米官方修复工具的角色（DHCP + TFTP），
     路由器开机进入恢复模式后会主动来拉取固件并自行刷写。

协议依据：小米官方 MIWIFIRepairTool 内置 Tftpd32 的真实日志（tftp.log）
  1) 路由器广播 DHCP Discover → 服务器分配 192.168.1.101
  2) 路由器向 TFTP(69) 发起 "Read request for file <4a.bin>. Mode octet"
  3) 固件传输完成后由路由器的 U-Boot 自行写入闪存

用法（必须 root，因为需要绑定 67/69 端口）：
  sudo /opt/homebrew/bin/python3 recovery_server.py [固件路径] [网卡]

默认固件：roms/miwifi_r4a_3.0.24_INT.bin
默认网卡：en14
"""

import os
import socket
import struct
import sys
import threading
import time

SERVER_IP = "192.168.1.100"
CLIENT_IP = "192.168.1.101"
IFACE = sys.argv[2] if len(sys.argv) > 2 else "en14"
HERE = os.path.dirname(os.path.abspath(__file__))
ROM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "roms", "miwifi_r4a_3.0.24_INT.bin")
BLOCK = 512

rom_data = open(ROM, "rb").read()
log_lock = threading.Lock()


def log(msg):
    with log_lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- 网卡配置
def setup_iface():
    """把网卡设成 192.168.1.100/24（脚本以 root 运行）"""
    log(f"配置 {IFACE} → {SERVER_IP}/24")
    os.system(f"ifconfig {IFACE} inet {SERVER_IP} netmask 255.255.255.0 up 2>/dev/null")
    time.sleep(1)
    out = os.popen(f"ifconfig {IFACE} | grep 'inet '").read().strip()
    log(f"  当前网卡: {out or '(未设置成功)'}")


# ---------------------------------------------------------------- DHCP 服务
def dhcp_reply(data, addr):
    if len(data) < 240:
        return None
    op, htype, hlen, hops, xid = struct.unpack("!BBBBI", data[:8])
    if op != 1:                       # BOOTREQUEST only
        return None
    chaddr = data[28:28 + 16]
    flags = struct.unpack("!H", data[10:12])[0]

    # 解析 options，找 message type (53)
    msg_type = None
    i = 240
    while i < len(data):
        code = data[i]
        if code == 255:
            break
        if code == 0:
            i += 1
            continue
        if i + 1 >= len(data):
            break
        ln = data[i + 1]
        if code == 53 and ln >= 1:
            msg_type = data[i + 2]
        i += 2 + ln

    if msg_type not in (1, 3):        # DISCOVER / REQUEST
        return None

    reply_type = 2 if msg_type == 1 else 5      # OFFER / ACK
    opts = b""
    opts += bytes([53, 1, reply_type])                       # message type
    opts += bytes([54, 4]) + socket.inet_aton(SERVER_IP)     # server identifier
    opts += bytes([51, 4]) + struct.pack("!I", 3600)         # lease time
    opts += bytes([1, 4]) + socket.inet_aton("255.255.255.0")  # subnet mask
    opts += bytes([3, 4]) + socket.inet_aton(SERVER_IP)      # router
    opts += bytes([6, 4]) + socket.inet_aton(SERVER_IP)      # dns
    opts += bytes([66, len(SERVER_IP)]) + SERVER_IP.encode()  # TFTP server
    opts += bytes([67, 8]) + b"4a.bin\x00\x00"               # bootfile name
    opts += b"\xff"

    pkt = struct.pack("!BBBBIHH", 2, 1, 6, 0, xid, 0, flags)
    pkt += socket.inet_aton("0.0.0.0")     # ciaddr
    pkt += socket.inet_aton(CLIENT_IP)     # yiaddr
    pkt += socket.inet_aton(SERVER_IP)     # siaddr (TFTP server)
    pkt += socket.inet_aton("0.0.0.0")     # giaddr
    pkt += chaddr[:16].ljust(16, b"\x00")
    pkt += b"\x00" * 64                    # sname
    pkt += b"4a.bin".ljust(128, b"\x00")   # file
    pkt += b"\x63\x82\x53\x63"             # magic cookie
    pkt += opts
    pkt += b"\x00" * max(0, 300 - len(pkt))

    kind = "OFFER" if reply_type == 2 else "ACK"
    log(f"DHCP {kind} → {CLIENT_IP}（请求方 MAC {':'.join('%02x' % b for b in chaddr[:6])}）")
    return pkt


def dhcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        s.bind(("0.0.0.0", 67))
    except PermissionError:
        log("❌ 绑定 67 端口失败 —— 请用 sudo 运行本脚本")
        sys.exit(1)
    # ★ 关键：把广播绑定到指定网卡，否则会从 Wi-Fi 发出去
    try:
        s.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(IFACE))
        log(f"DHCP 已绑定网卡 {IFACE}（索引 {socket.if_nametoindex(IFACE)}）")
    except Exception as e:
        log(f"⚠️ IP_BOUND_IF 失败: {e}")
    log("DHCP 服务已启动（UDP 67）")
    while True:
        try:
            data, addr = s.recvfrom(2048)
            log(f"📨 收到 DHCP 包 {len(data)} 字节 来自 {addr[0]}:{addr[1]}")
            rep = dhcp_reply(data, addr)
            if rep:
                s.sendto(rep, ("255.255.255.255", 68))
        except Exception as e:
            log(f"DHCP 异常: {e}")


# ---------------------------------------------------------------- TFTP 服务
def tftp_session(req, client, name):
    """处理一次 RRQ：任意文件名都返回同一个固件（最稳妥）"""
    log(f"📥 收到 TFTP 读请求: <{name}>  来自 {client[0]}:{client[1]}  —— 开始传输")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 0))
    s.settimeout(5)

    total = len(rom_data)
    nblocks = (total + BLOCK - 1) // BLOCK
    sent = 0
    t0 = time.time()
    try:
        for bn in range(1, nblocks + 1):
            chunk = rom_data[(bn - 1) * BLOCK: bn * BLOCK]
            pkt = struct.pack("!HH", 3, bn) + chunk
            for attempt in range(6):
                s.sendto(pkt, client)
                try:
                    ack, _ = s.recvfrom(1024)
                    if len(ack) >= 4 and struct.unpack("!H", ack[:2])[0] == 4 \
                            and struct.unpack("!H", ack[2:4])[0] == bn:
                        break
                except socket.timeout:
                    if attempt == 5:
                        log(f"⚠️ 第 {bn} 块重传 5 次仍无响应，放弃本次传输")
                        raise
            sent += len(chunk)
            if bn % 5000 == 0:
                log(f"   进度 {bn}/{nblocks} 块（{sent/1048576:.1f}/{total/1048576:.1f} MB）")
    except Exception as e:
        log(f"❌ 传输中断于第 {bn} 块: {e}")
        s.close()
        return
    s.close()
    dt = time.time() - t0
    log(f"✅ 传输完成: {sent} 字节 / {nblocks} 块，用时 {dt:.1f}s "
        f"（{sent/1048576/max(dt,0.01):.1f} MB/s）")
    log("   → 路由器应已开始自行刷写。**此时千万不要断电**，等待它重启（约 2-4 分钟）")


def tftp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", 69))
    except PermissionError:
        log("❌ 绑定 69 端口失败 —— 请用 sudo 运行本脚本")
        sys.exit(1)
    try:
        tsock.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(IFACE))
    except Exception:
        pass
    log("TFTP 服务已启动（UDP 69，任意文件名都返回固件）")
    while True:
        try:
            data, addr = s.recvfrom(2048)
            if len(data) < 4:
                continue
            opcode = struct.unpack("!H", data[:2])[0]
            if opcode != 1:               # 只处理 RRQ
                continue
            parts = data[2:].split(b"\x00")
            name = parts[0].decode("utf-8", "replace")
            threading.Thread(target=tftp_session, args=(data, addr, name), daemon=True).start()
        except Exception as e:
            log(f"TFTP 异常: {e}")


# ---------------------------------------------------------------- 主流程
if __name__ == "__main__":
    print("=" * 62)
    print(" 小米路由器 4A 千兆版 —— 恢复模式救援服务器")
    print("=" * 62)
    print(f"  固件    : {ROM}")
    print(f"  大小    : {len(rom_data)} 字节 ({len(rom_data)/1048576:.2f} MB)")
    print(f"  网卡    : {IFACE}")
    print(f"  本机 IP : {SERVER_IP}   分配给路由器: {CLIENT_IP}")
    print("=" * 62)
    if os.geteuid() != 0:
        print("  ⚠️  当前不是 root，绑定 67/69 端口会失败。")
        print("     请用： sudo python3 recovery_server.py")
        sys.exit(1)

    setup_iface()
    threading.Thread(target=dhcp_server, daemon=True).start()
    threading.Thread(target=tftp_server, daemon=True).start()
    log("等待路由器进入恢复模式并请求固件……（按 Ctrl+C 退出）")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        log("已手动停止")
