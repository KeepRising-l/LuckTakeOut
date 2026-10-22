// 端到端验证「再点一单 → 确认并支付」：点按钮 → 确认 → 等待支付 → 截订单详情
const { spawn } = require('child_process');
const fs = require('fs');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9448;
const OUT = 'E:/pythonTakeOut/web/screenshots';

const chrome = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:/Users/Li/AppData/Local/Temp/chrome-cdp-reorder',
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
    const res = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    return res.result && res.result.result && res.result.result.value;
  };
  const shoot = async (file) => {
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(`${OUT}/${file}`, Buffer.from(shot.result.data, 'base64'));
    console.log('saved', file);
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390, height: 900, deviceScaleFactor: 2, mobile: true,
  });

  await send('Page.navigate', { url: 'http://localhost:5173/login' });
  await sleep(3000);
  console.log('login:', await evaluate(`(async () => {
    const r = await fetch('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '13700000001', code: '123456' }),
    });
    const j = await r.json();
    if (!j.data) return 'FAIL';
    localStorage.setItem('takeout:customerToken', j.data.accessToken);
    localStorage.setItem('takeout:customerInfo', JSON.stringify(j.data.user));
    return 'OK';
  })()`));

  await send('Page.navigate', { url: 'http://localhost:5173/' });
  await sleep(5000);

  console.log('click reorder:', await evaluate(`(() => {
    const btn = [...document.querySelectorAll('button')].find(b => /再点一单/.test(b.textContent || ''));
    if (!btn) return 'not found';
    btn.click();
    return 'ok';
  })()`));
  await sleep(2000);

  console.log('confirm pay:', await evaluate(`(() => {
    const btn = [...document.querySelectorAll('.van-dialog__confirm, button')]
      .find(b => /确认并支付/.test(b.textContent || ''));
    if (!btn) return 'confirm not found';
    btn.click();
    return 'ok';
  })()`));
  await sleep(5000);

  console.log('url:', await evaluate('location.pathname + location.search'));
  await shoot('reorder-paid-order.png');

  ws.close();
  chrome.kill();
  process.exit(0);
})().catch((e) => {
  console.error(e);
  chrome.kill();
  process.exit(1);
});
