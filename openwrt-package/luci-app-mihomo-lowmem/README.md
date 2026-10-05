# luci-app-mihomo-lowmem

LuCI front-end for [mihomo-lowmem](#). / mihomo-lowmem 的 LuCI 管理界面。

## Features / 功能

| Feature | 功能 |
|---|---|
| Service status + restart | 服务状态与重启 |
| Proxy list with one-tap switching | 线路列表，一键切换 |
| **Subscription update from the device** | **由本设备拉取订阅**（路由器不联网）|
| Log viewer (last 200 lines) | 日志查看（末 200 行）|
| Memory hint | 内存提示 |

## How it works / 工作原理

The view talks **directly to the mihomo REST API** (`:9990`) — no extra backend,
no extra daemon, **no extra memory**. Enable CORS in `config.yaml`:

界面**直接调用 mihomo 的 REST API**（`:9990`）—— 不需要额外后端、
不需要额外守护进程、**不占额外内存**。请在 `config.yaml` 里开启 CORS：

```yaml
external-controller-cors:
  allow-origins:
    - 'http://192.168.1.1'      # ← your router's LAN address
    - 'http://192.168.31.1'
  allow-private-network: true
```

> `mihomo` rejects `*` for `allow-origins` — list the addresses explicitly.
> `mihomo` 不接受 `allow-origins: *`，必须显式列出地址。

Only the **restart** action goes through rpcd (`fs.exec('/etc/init.d/mihomo')`),
which is why the ACL in `root/usr/share/rpcd/acl.d/` is intentionally narrow:
it can read two status files and execute three scripts — nothing else.

只有**重启**动作通过 rpcd（`fs.exec('/etc/init.d/mihomo')`），
因此 `root/usr/share/rpcd/acl.d/` 里的 ACL 刻意收得很窄：
只能读两个状态文件、执行三个脚本，别的什么都不行。

## Install / 安装

```sh
# as part of a buildroot
make menuconfig     # LuCI -> Applications -> luci-app-mihomo-lowmem
# or build the ipk directly
make package/luci-app-mihomo-lowmem/compile V=s
```

## Layout / 目录结构

```
luci-app-mihomo-lowmem/
├── Makefile
├── htdocs/luci-static/resources/view/mihomo-lowmem/overview.js   # the view
└── root/
    ├── etc/uci-defaults/luci-app-mihomo-lowmem                   # first-run defaults
    └── usr/share/
        ├── luci/menu.d/luci-app-mihomo-lowmem.json               # menu entry
        └── rpcd/acl.d/luci-app-mihomo-lowmem.json                # permissions
```
