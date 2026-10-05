#
# mihomo-lowmem :: OpenWrt package
# 内存优化版 mihomo 的 OpenWrt 软件包
#
# This package builds mihomo with `with_low_memory` so that it can run on
# routers with as little as ~47 MB of usable RAM (e.g. MT7621A + 128 MB).
# 本软件包以 `with_low_memory` 标签编译 mihomo，
# 使其可运行在仅约 47MB 可用内存的路由器上（如 MT7621A + 128MB）。
#
include $(TOPDIR)/rules.mk

PKG_NAME:=mihomo-lowmem
PKG_VERSION:=1.18.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/MetaCubeX/mihomo.git
PKG_SOURCE_VERSION:=v$(PKG_VERSION)
PKG_MIRROR_HASH:=skip
PKG_BUILD_DEPENDS:=golang/host
PKG_BUILD_PARALLEL:=1

GO_PKG:=github.com/metacubex/mihomo
GO_PKG_LDFLAGS_X:=github.com/metacubex/mihomo/constant.Version=$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/golang/golang-package.mk

define Package/$(PKG_NAME)
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=Web Servers/Proxies
  TITLE:=Memory-optimized mihomo (Clash.Meta) core
  DEPENDS:=$(GO_ARCH_DEPENDS) +ca-bundle +xz
  URL:=https://github.com/MetaCubeX/mihomo
  PKGARCH:=$(GO_ARCH)
endef

define Package/$(PKG_NAME)/description
  Memory-optimized mihomo core for resource-constrained OpenWrt routers.
  Built with the `with_low_memory` tag and aggressive GC defaults so it
  can coexist with the rest of the system on devices with ~47 MB of
  usable RAM (MT7621A / 128 MB class).

  面向内存受限 OpenWrt 路由器的精简版 mihomo 内核。
  使用 `with_low_memory` 标签编译并配合激进的 GC 参数，
  可在仅约 47MB 可用内存的设备（MT7621A / 128MB 级别）上稳定运行。
endef

define Build/Compile
	$(call GoPackage/Build/Compile)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(GO_PKG_BUILD_BIN_DIR)/mihomo $(1)/usr/bin/mihomo-lowmem
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/mihomo.init $(1)/etc/init.d/mihomo-lowmem
	$(INSTALL_DIR) $(1)/etc/mihomo-lowmem
	$(INSTALL_CONF) ./files/config.template.yaml $(1)/etc/mihomo-lowmem/config.yaml
	$(INSTALL_DIR) $(1)/usr/share/mihomo-lowmem
	$(INSTALL_BIN) ./files/start.sh   $(1)/usr/share/mihomo-lowmem/start.sh
	$(INSTALL_BIN) ./files/restart.sh $(1)/usr/share/mihomo-lowmem/restart.sh
	$(INSTALL_DATA) ./files/nft.rules $(1)/usr/share/mihomo-lowmem/nft.rules
endef

define Package/$(PKG_NAME)/conffiles
/etc/mihomo-lowmem/config.yaml
endef

$(eval $(call GoBinPackage,$(PKG_NAME)))
$(eval $(call BuildPackage,$(PKG_NAME)))
