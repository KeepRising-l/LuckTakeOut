const http = require('http');
const httpProxy = require('http-proxy-middleware');
const express = require('express');
const path = require('path');

const app = express();

// 静态文件服务
app.use(express.static('.'));

// API代理
const apiProxy = httpProxy.createProxyMiddleware('/api', {
  target: 'http://localhost:8091',
  changeOrigin: true,
  logLevel: 'debug'
});

app.use('/api', apiProxy);

// 启动服务器
const PORT = 8083;
app.listen(PORT, () => {
  console.log(`代理服务器运行在 http://localhost:${PORT}`);
  console.log('静态文件: http://localhost:' + PORT);
  console.log('API代理: http://localhost:' + PORT + '/api -> http://localhost:8091/api');
});