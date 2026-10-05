# Visual guide / 图示说明

## Included diagrams / 已包含的图

| File | What it shows | 说明 |
|---|---|---|
| [`memory-budget.svg`](memory-budget.svg) | The whole reason this project exists: 49 MB of demand against 47 MB of usable RAM, and how the optimizations bring it to 40 MB. | 本项目存在的理由：49MB 需求 vs 47MB 可用内存，以及优化如何把它压到 40MB。|
| [`architecture.svg`](architecture.svg) | Component layout, data path, and the flash/tmpfs split. | 组件布局、数据流，以及闪存/内存盘的分工。|
| [`subscription-flow.svg`](subscription-flow.svg) | The device-side subscription update, step by step. | 设备端更新订阅的分步流程。|

All three are hand-written SVG: no binaries in git history, no export step, and
they stay sharp at any zoom. Edit them in any text editor.

三张图都是手写 SVG：git 历史里没有二进制、不需要导出步骤、任意缩放都清晰，
用任意文本编辑器即可修改。

## Viewing them / 如何查看

- **On GitHub:** rendered automatically in the README.
- **Locally:** open with a **browser** (drag the file into a browser window).
  Do *not* double-click on macOS if your default `.svg` handler is a text editor —
  you will see the source, not the picture.
- **Converting to PNG** (for slide decks, chat, etc.):

```sh
# any one of these will do
rsvg-convert -w 1760 memory-budget.svg -o memory-budget.png
inkscape --export-type=png --export-width=1760 memory-budget.svg
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
  --window-size=880,430 --screenshot=memory-budget.png \
  "file://$PWD/memory-budget.svg"
```

## How to add real screenshots / 如何补充真实截图

Screenshots of a real deployment are very welcome. Please follow these rules:

**1. Sanitise before you capture.** A router dashboard leaks a lot: SSIDs,
subscription URLs, node names, public IPs, device hostnames. Blur or replace them.

**2. Suggested set / 建议的截图组**

| Filename | What to capture | 拍什么 |
|---|---|---|
| `screenshot-dashboard.png` | the dashboard overview (`:9990/ui/`) | 管理面板总览 |
| `screenshot-nodes.png` | the node list with latency results | 线路列表与延迟结果 |
| `screenshot-subscribe.png` | the subscription button mid-update | 更新订阅进行中 |
| `screenshot-luci.png` | the LuCI view (`admin/services/mihomo-lowmem`) | LuCI 界面 |
| `screenshot-memory.png` | `free` output after boot | 开机后的 `free` 输出 |

**3. Size and format / 尺寸与格式**

- PNG, width 1200–1600 px, cropped to the relevant area
- keep each file under ~300 KB (use `oxipng`/`pngquant` if needed)
- name them exactly as above so the README can reference them

**4. Wire them into the README / 接入 README**

Add a section like this after the "Highlights" table:

```markdown
### Screenshots / 界面截图

![Dashboard](docs/images/screenshot-dashboard.png)
![Node list](docs/images/screenshot-nodes.png)
![LuCI view](docs/images/screenshot-luci.png)
```

**5. Checklist / 检查清单**

- [ ] no SSID, no password, no subscription URL, no node name
- [ ] no public IP or MAC address
- [ ] no account name, email or device hostname
- [ ] no browser bookmarks/tabs visible
- [ ] numbers still legible after compression

## Why the diagrams are not screenshots / 为什么用图示而不是截图

A screenshot shows one deployment on one day. The diagrams show the *design*, which
is what a reader needs in order to decide whether the project applies to their router.
Screenshots are a nice complement once you have a deployment you are happy with.

截图展示的是某一天某一台设备的状态；图示展示的是**设计**——
而读者需要先看懂设计，才能判断这个项目是否适用于自己的路由器。
当你有了满意的实机环境，截图是很好的补充。
