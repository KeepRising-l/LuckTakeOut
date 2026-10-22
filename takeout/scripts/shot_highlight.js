// 亮点功能验证截图：首页「猜你想吃」+ AI 对话推荐 + 再点一单确认弹窗
const { spawn } = require('child_process');
const fs = require('fs');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9447;
const OUT = 'E:/pythonTakeOut/web/screenshots';

const chrome = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:/Users/Li/AppData/Local/Temp/chrome-cdp-highlight',
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
    if (!j.data || !j.data.accessToken) return 'FAIL';
    localStorage.setItem('takeout:customerToken', j.data.accessToken);
    localStorage.setItem('takeout:customerInfo', JSON.stringify(j.data.user));
    return 'OK';
  })()`));

  // 1) 首页：猜你想吃
  await send('Page.navigate', { url: 'http://localhost:5173/' });
  await sleep(5000);
  await shoot('home-recommend.png');

  // 2) 首页滚动到推荐区后再拍一张（确保完整可见）
  await evaluate(`(() => {
    const el = document.querySelector('.rec-block');
    if (el) el.scrollIntoView({ block: 'center' });
    return !!el;
  })()`);
  await sleep(800);
  await shoot('home-recommend-focus.png');

  // 3) AI 对话：问推荐，等待回复
  await send('Page.navigate', { url: 'http://localhost:5173/ai' });
  await sleep(3500);
  console.log('send:', await evaluate(`(async () => {
    const input = document.querySelector('.chat-input input, .composer input, input[type=text]');
    if (!input) return 'no input';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, '今天吃什么好，推荐一下');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(r => setTimeout(r, 300));
    const btn = [...document.querySelectorAll('button')].find(b => /发送/.test(b.textContent || ''));
    if (!btn) return 'no send button';
    btn.click();
    return 'sent';
  })()`));
  await sleep(6000);
  await shoot('ai-recommend-chat.png');

  // 4) 首页点「再点一单」，截确认弹窗
  await send('Page.navigate', { url: 'http://localhost:5173/' });
  await sleep(4500);
  console.log('reorder:', await evaluate(`(() => {
    const btn = [...document.querySelectorAll('button')].find(b => /再点一单/.test(b.textContent || ''));
    if (!btn) return 'no reorder button';
    btn.click();
    return 'clicked';
  })()`));
  await sleep(2500);
  await shoot('reorder-confirm.png');

  ws.close();
  chrome.kill();
  process.exit(0);
})().catch((e) => {
  console.error(e);
  chrome.kill();
  process.exit(1);
});
