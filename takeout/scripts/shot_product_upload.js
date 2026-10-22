// 商户端菜品图片上传的端到端验证：
// 登录 → 菜品管理 → 打开新增弹窗 → 选择本地图片（真实走 el-upload）→ 截图 → 填名称 → 保存 → 截图列表
const { spawn } = require('child_process');
const fs = require('fs');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9446;
const OUT = 'E:/pythonTakeOut/web/screenshots';
const LOCAL_IMAGE = 'E:/pythonTakeOut/takeout/media/products/sichuan/chili_pork.jpg';

const chrome = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:/Users/Li/AppData/Local/Temp/chrome-cdp-upload',
  '--no-sandbox',
  '--disable-gpu',
  'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('chrome devtools not ready');
}

(async () => {
  const ws = new WebSocket(await getWsUrl());
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  };
  await new Promise((r) => { ws.onopen = r; });
  const send = (method, params = {}) => new Promise((resolve) => {
    const mid = ++id;
    pending.set(mid, resolve);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evaluate = async (expression) => {
    const res = await send('Runtime.evaluate', {
      expression, awaitPromise: true, returnByValue: true,
    });
    return res.result && res.result.result && res.result.result.value;
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('DOM.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  await send('Page.navigate', { url: 'http://localhost:5174/login' });
  await sleep(3000);

  console.log('login:', await evaluate(`(async () => {
    const r = await fetch('/api/merchant/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'merchant1', password: 'merchant123' }),
    });
    const j = await r.json();
    if (!j.data || !j.data.token) return 'FAIL';
    localStorage.setItem('takeout:merchantToken', j.data.token);
    localStorage.setItem('takeout:merchantInfo', JSON.stringify({
      merchantId: j.data.merchantId, merchantName: j.data.merchantName,
      avatar: j.data.avatar, status: j.data.status,
    }));
    return 'OK';
  })()`));

  await send('Page.navigate', { url: 'http://localhost:5174/#/products' });
  await sleep(4000);

  // 点击「新增菜品」
  console.log('open dialog:', await evaluate(`(() => {
    const btn = [...document.querySelectorAll('.el-button')].find(b => b.textContent.trim() === '新增菜品');
    if (!btn) return 'button not found';
    btn.click();
    return 'clicked';
  })()`));
  await sleep(1200);

  // 通过 CDP 给隐藏 file input 设置文件，触发真实上传流程
  const doc = await send('DOM.getDocument', { depth: -1 });
  const input = await send('DOM.querySelector', {
    nodeId: doc.result.root.nodeId,
    selector: '.img-upload input[type=file]',
  });
  if (!input.result.nodeId) throw new Error('file input not found');
  await send('DOM.setFileInputFiles', {
    nodeId: input.result.nodeId,
    files: [LOCAL_IMAGE],
  });
  await sleep(3000);

  console.log('preview src:', await evaluate(`(() => {
    const img = document.querySelector('.img-box img');
    return img ? img.getAttribute('src') : 'no preview';
  })()`));

  const shot1 = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(`${OUT}/merchant-product-upload-dialog.png`, Buffer.from(shot1.result.data, 'base64'));
  console.log('saved merchant-product-upload-dialog.png');

  // 仅截图弹窗（保存流程已在上一轮验证过，避免反复产生测试数据）
  ws.close();
  chrome.kill();
  process.exit(0);
})().catch((e) => {
  console.error(e);
  chrome.kill();
  process.exit(1);
});
