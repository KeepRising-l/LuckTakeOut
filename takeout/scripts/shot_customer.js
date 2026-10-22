// 通过 CDP 注入登录态后截图：首页商户列表 + 咖啡店 + 寿司店
const { spawn } = require('child_process');
const fs = require('fs');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9444;
const OUT = 'E:/pythonTakeOut/web/screenshots';

const chrome = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:/Users/Li/AppData/Local/Temp/chrome-cdp-seed2',
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

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390, height: 844, deviceScaleFactor: 2, mobile: true,
  });

  // 1) 打开同源页面，接口登录并写入 localStorage
  await send('Page.navigate', { url: 'http://localhost:5173/login' });
  await sleep(3500);

  const login = await send('Runtime.evaluate', {
    expression: `(async () => {
      const r = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: '13700000001', code: '123456' }),
      });
      const j = await r.json();
      if (!j || !j.data || !j.data.accessToken) return 'FAIL ' + JSON.stringify(j).slice(0, 200);
      localStorage.setItem('takeout:customerToken', j.data.accessToken);
      localStorage.setItem('takeout:customerInfo', JSON.stringify(j.data.user));
      return 'OK';
    })()`,
    awaitPromise: true,
    returnByValue: true,
  });
  console.log('login:', login.result && login.result.result && login.result.result.value);

  const shoot = async (path, file) => {
    await send('Page.navigate', { url: path });
    await sleep(4500);
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(`${OUT}/${file}`, Buffer.from(shot.result.data, 'base64'));
    console.log('saved', file);
  };

  await shoot('http://localhost:5173/', 'home-merchants.png');
  await shoot('http://localhost:5173/shop/1', 'shop-sichuan.png');
  await shoot('http://localhost:5173/shop/2', 'shop-milktea.png');
  await shoot('http://localhost:5173/shop/3', 'shop-coffee.png');
  await shoot('http://localhost:5173/shop/4', 'shop-noodle.png');
  await shoot('http://localhost:5173/shop/5', 'shop-fastfood.png');
  await shoot('http://localhost:5173/shop/6', 'shop-sushi.png');

  ws.close();
  chrome.kill();
  process.exit(0);
})().catch((e) => {
  console.error(e);
  chrome.kill();
  process.exit(1);
});
