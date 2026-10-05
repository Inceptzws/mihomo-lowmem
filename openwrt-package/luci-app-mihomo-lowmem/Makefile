#
# luci-app-mihomo-lowmem :: LuCI front-end
# LuCI 前端界面（OpenWrt 上游标准形式）
#
include $(TOPDIR)/rules.mk

LUCI_TITLE:=LuCI support for mihomo-lowmem
LUCI_DEPENDS:=+luci-base +mihomo-lowmem
LUCI_PKGARCH:=all

PKG_NAME:=luci-app-mihomo-lowmem
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
# 调用 BuildPackage —— OpenWrt 编译环境的入口
$(eval $(call BuildPackage,$(PKG_NAME)))
