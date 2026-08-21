// Weighbridge Bridge — indicator (TCP) aur CCTV cameras ko browser tak laata hai.
// Chalane ka tareeka: neeche README section dekho.

const net = require('net');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const configPath = path.join(__dirname, 'bridge-config.json');
const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const weightRegex = new RegExp(cfg.weightRegex, 'g');

let latestWeight = { value: null, stable: null, raw: '', ts: null, connected: false };
const wsClients = new Set();

function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const ws of wsClients) {
    if (ws.readyState === ws.OPEN) ws.send(data);
  }
}

// ---- Indicator TCP connection ----
function connectIndicator() {
  const socket = new net.Socket();
  let buffer = '';

  socket.connect(cfg.indicatorPort, cfg.indicatorHost, () => {
    console.log('[indicator] connected to ' + cfg.indicatorHost + ':' + cfg.indicatorPort);
    latestWeight.connected = true;
    broadcast({ type: 'status', connected: true });
  });

  socket.on('data', (chunk) => {
    buffer += chunk.toString('utf8');
    let idx;
    while ((idx = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (!line) continue;
      parseLine(line);
    }
    // agar indicator \n nahi bhejta, to har chunk ko bhi try karo
    if (buffer.length > 200) { parseLine(buffer); buffer = ''; }
  });

  socket.on('error', (err) => {
    console.error('[indicator] error:', err.message);
  });

  socket.on('close', () => {
    console.log('[indicator] connection closed, retrying in 3s...');
    latestWeight.connected = false;
    broadcast({ type: 'status', connected: false });
    setTimeout(connectIndicator, 3000);
  });
}

function parseLine(line) {
  const matches = line.match(weightRegex);
  if (!matches || matches.length === 0) return;
  const value = parseFloat(matches[matches.length - 1]);
  if (Number.isNaN(value)) return;

  let stable = null;
  if (cfg.stableToken && line.indexOf(cfg.stableToken) !== -1) stable = true;
  else if (cfg.unstableToken && line.indexOf(cfg.unstableToken) !== -1) stable = false;

  latestWeight = { value, stable, raw: line, ts: Date.now(), connected: true };
  broadcast({ type: 'weight', ...latestWeight });
}

// ---- Camera snapshot proxy (fixes CORS + keeps camera creds off the browser) ----
async function fetchCamera(url) {
  const headers = {};
  if (cfg.cameraUser) {
    const auth = Buffer.from(cfg.cameraUser + ':' + (cfg.cameraPassword || '')).toString('base64');
    headers['Authorization'] = 'Basic ' + auth;
  }
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error('camera fetch failed: ' + res.status);
  const buf = Buffer.from(await res.arrayBuffer());
  return { buf, contentType: res.headers.get('content-type') || 'image/jpeg' };
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const pathname = req.url.split('?')[0];

  if (pathname === '/health') {
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ ok: true, indicatorConnected: latestWeight.connected }));
    return;
  }

  if (pathname === '/camera/top' || pathname === '/camera/side') {
    const camUrl = pathname === '/camera/top' ? cfg.topCameraSnapshotUrl : cfg.sideCameraSnapshotUrl;
    try {
      const { buf, contentType } = await fetchCamera(camUrl);
      res.setHeader('Content-Type', contentType);
      res.setHeader('Cache-Control', 'no-store');
      res.end(buf);
    } catch (err) {
      res.statusCode = 502;
      res.end('camera error: ' + err.message);
    }
    return;
  }

  res.statusCode = 404;
  res.end('not found');
});

const wss = new WebSocketServer({ server });
wss.on('connection', (ws) => {
  wsClients.add(ws);
  ws.send(JSON.stringify({ type: 'weight', ...latestWeight }));
  ws.on('close', () => wsClients.delete(ws));
});

server.listen(cfg.httpPort, () => {
  console.log('Weighbridge bridge running on http://localhost:' + cfg.httpPort);
  console.log('  Live weight: ws://localhost:' + cfg.httpPort);
  console.log('  Top camera:  http://localhost:' + cfg.httpPort + '/camera/top');
  console.log('  Side camera: http://localhost:' + cfg.httpPort + '/camera/side');
});

connectIndicator();

/*
README — Weighbridge Bridge Setup
==================================
Ye bridge weighbridge.html aur real hardware (indicator + CCTV) ke beech
mein chalta hai, kyunki browser seedha raw TCP socket ya password-protected
cross-network camera se baat nahi kar sakta.

1. PC par Node.js install karo (v18+): https://nodejs.org
2. is 'bridge' folder me terminal khol ke:
     npm install
3. 'bridge-config.json' edit karo:
     - indicatorHost/indicatorPort: weighbridge indicator ka LAN IP aur
       TCP port (indicator ya uske RS232-to-Ethernet converter ki manual
       me likha hota hai; common ports: 4001, 8899, 2000).
     - weightRegex: indicator jo text bhejta hai usme se number nikalne
       ka pattern. Default kaam kar jaata hai agar sirf number aata hai.
     - topCameraSnapshotUrl / sideCameraSnapshotUrl: camera ka snapshot
       JPEG URL (camera settings me milta hai, jaise
       http://192.168.1.101/snapshot.jpg ya /cgi-bin/snapshot.cgi).
     - cameraUser/cameraPassword: agar camera login maangta hai.
4. Chalao:
     node server.js
   "Weighbridge bridge running..." dikhna chahiye.
5. weighbridge.html kholo, Settings tab me "Bridge Address" me
   http://localhost:8090 confirm karo (ye default hai), fir Weighment
   tab me "Connect Indicator" dabao.

Agar bridge PC (jaha browser chal raha hai) se alag machine par chala
rahe ho, to Bridge Address me us machine ka IP daalo
(jaise http://192.168.1.50:8090) — indicatorHost/Port aur camera URLs
bridge ke config me hi rehte hain, browser me nahi.
*/
