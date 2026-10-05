'use strict';
'require view';
'require fs';
'require ui';
'require rpc';
'require uci';

/*
 * mihomo-lowmem :: LuCI overview
 * mihomo-lowmem :: LuCI 总览界面
 *
 * Design notes / 设计说明:
 *   - The view talks to the mihomo REST API directly (:9990) so it does not
 *     need any extra backend. CORS is enabled in the config template.
 *     本界面直接调用 mihomo 的 REST API（:9990），因此不需要额外后端。
 *     CORS 已在配置模板中开启。
 *   - The subscription button performs a DEVICE-SIDE fetch: your browser
 *     downloads it and POSTs the body to the router. The router itself never
 *     opens an outbound connection for this.
 *     订阅按钮执行的是【设备端拉取】：由你的浏览器下载后 POST 给路由器，
 *     路由器本身不会为此发起任何对外连接。
 */

var API = 'http://' + window.location.hostname + ':9990';
var CGI = 'http://' + window.location.hostname + '/cgi-bin/save-sub';

function api(path, opt) {
	return fetch(API + path, opt).then(function (r) { return r.json(); });
}

return view.extend({
	load: function () {
		return Promise.all([
			L.resolveDefault(fs.read('/tmp/mihomo-status'), 'unknown'),
			L.resolveDefault(api('/version'), {}),
			L.resolveDefault(api('/proxies'), { proxies: {} })
		]);
	},

	render: function (data) {
		var status = (data[0] || '').trim();
		var version = (data[1] || {}).version || '-';
		var proxies = (data[2] || {}).proxies || {};
		// the group name is configurable — accept both common spellings
		// 分组名可配置 —— 两种常见写法都兼容
		var GROUP = proxies['🚀 Select'] ? '🚀 Select'
		          : (proxies['🚀节点选择'] ? '🚀节点选择' : null);
		var group = GROUP ? proxies[GROUP] : {};
		var nodes = group.all || [];

		var memBox = E('div', { 'class': 'cbi-value' }, [
			E('label', { 'class': 'cbi-value-title' }, 'Memory / 内存'),
			E('div', { 'class': 'cbi-value-field' }, [
				E('span', { 'id': 'mem' }, '...'),
				E('span', { 'style': 'margin-left:12px;color:#888' },
					'(run `free` over SSH for exact values / 精确值请用 SSH 执行 free)')
			])
		]);

		var statusBox = E('div', { 'class': 'cbi-value' }, [
			E('label', { 'class': 'cbi-value-title' }, 'Service / 服务'),
			E('div', { 'class': 'cbi-value-field' }, [
				E('span', { 'class': 'label ' + (status === 'OK' ? 'success' : 'warning') },
					status === 'OK' ? 'running / 运行中' : status),
				E('span', { 'style': 'margin-left:12px;color:#888' }, 'core ' + version)
			])
		]);

		var btns = E('div', { 'class': 'cbi-page-actions' }, [
			E('button', {
				'class': 'btn cbi-button cbi-button-apply',
				'click': ui.createHandlerFn(this, function () {
					ui.showModal(null, [ E('p', { 'class': 'spinning' }, 'Restarting… / 正在重启…') ]);
					return fs.exec('/etc/init.d/mihomo', ['restart'])
						.then(function () { ui.hideModal(); ui.addNotification(null, E('p', {}, 'Restarted / 已重启')); })
						.catch(function (e) { ui.hideModal(); ui.addNotification(null, E('p', {}, String(e))); });
				})
			}, 'Restart / 重启'),
			E('button', {
				'class': 'btn cbi-button cbi-button-action',
				'click': ui.createHandlerFn(this, function () {
					var self = this;
					ui.showModal(null, [ E('p', { 'class': 'spinning' }, 'Fetching on this device… / 正在用本设备拉取…') ]);
					return fetch(uci.get('mihomo-lowmem', 'general', 'sub_url') || '', { cache: 'no-store' })
						.then(function (r) { return r.text(); })
						.then(function (body) {
							return fetch(CGI, { method: 'POST', body: body });
						})
						.then(function (r) { return r.json(); })
						.then(function (j) {
							ui.hideModal();
							ui.addNotification(null, E('p', {},
								j.ok ? ('OK: ' + j.nodes + ' proxies, ' + j.size + ' bytes')
								     : ('Failed / 失败: ' + (j.error || '?'))));
						})
						.catch(function (e) {
							ui.hideModal();
							ui.addNotification(null, E('p', {}, String(e)));
						});
				})
			}, 'Update subscription (this device) / 更新订阅（本设备）')
		]);

		var nodeRows = nodes.map(function (n) {
			var active = (group.now === n);
			return E('tr', { 'class': active ? 'tr' : '' }, [
				E('td', {}, n),
				E('td', { 'class': 'cbi-section-table-cell' },
					E('button', {
						'class': 'btn cbi-button cbi-button-' + (active ? 'disabled' : 'action'),
						'disabled': active,
						'click': ui.createHandlerFn(this, function () {
							return api('/proxies/' + encodeURIComponent(GROUP), {
								method: 'PUT',
								headers: { 'Content-Type': 'application/json' },
								body: JSON.stringify({ name: n })
							}).then(function () { window.location.reload(); });
						})
					}, active ? 'current / 当前' : 'switch / 切换'))
			]);
		});

		var table = E('table', { 'class': 'table' }, [
			E('tr', { 'class': 'tr table-titles' }, [ E('th', {}, 'Proxy'), E('th', {}, '') ])
		].concat(nodeRows));

		var logBox = E('div', {}, [
			E('button', {
				'class': 'btn cbi-button',
				'click': ui.createHandlerFn(this, function () {
					var self = this;
					return fs.read('/tmp/clash.log').then(function (s) {
						ui.showModal('Log / 日志', [
							E('pre', { 'style': 'max-height:60vh;overflow:auto;white-space:pre-wrap' },
								s.split('\n').slice(-200).join('\n')),
							E('div', { 'class': 'right' },
								E('button', { 'class': 'btn', 'click': ui.hideModal }, 'Close / 关闭'))
						]);
					});
				})
			}, 'Show log / 查看日志')
		]);

		return E([
			E('h2', {}, 'Mihomo (LowMem)'),
			E('div', { 'class': 'cbi-map' }, [
				E('div', { 'class': 'cbi-section' }, [ statusBox, memBox ]),
				E('div', { 'class': 'cbi-section' }, [ btns ]),
				E('div', { 'class': 'cbi-section' }, [
					E('h3', {}, 'Proxies (' + nodes.length + ') / 线路'),
					table
				]),
				E('div', { 'class': 'cbi-section' }, [ logBox ])
			])
		]);
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
