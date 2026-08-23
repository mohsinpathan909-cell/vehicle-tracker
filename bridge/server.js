// Weighbridge Bridge — IN aur OUT, dono indicator (TCP) + unke CCTV cameras ko
// browser tak laata hai. Chalane ka tareeka: neeche README section dekho.

const net = require('net');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const configPath = path.join(__dirname, 'bridge-config.json');
const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const weightRegex = new RegExp(cfg.weightRegex, 'g');
const STATIONS = Object.keys(cfg.stations); // ['in', 'out']

const latest = {};
for (const st of STATIONS) latest[st] = { value: null, stable: null, raw: '', ts: null, connected: false };

const wsClients = new Set();
function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const ws of wsClients) {
    if (ws.readyState === ws.OPEN) ws.send(data);
  }
}

// ---- Indicator TCP connections (one per station) ----
function connectIndicator(station) {
  const stCfg = cfg.stations[station];
  const socket = new net.Socket();
  let buffer = '';

  socket.connect(stCfg.indicatorPort, stCfg.indicatorHost, () => {
    console.log('[' + station + '] indicator connected to ' + stCfg.indicatorHost + ':' + stCfg.indicatorPort);
    latest[station].connected = true;
    broadcast({ type: 'status', station, connected: true });
  });

  socket.on('data', (chunk) => {
    buffer += chunk.toString('utf8');
    let idx;
    while ((idx = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line) parseLine(station, line);
    }
    if (buffer.length > 200) { parseLine(station, buffer); buffer = ''; }
  });

  socket.on('error', (err) => {
    console.error('[' + station + '] indicator error:', err.message);
  });

  socket.on('close', () => {
    console.log('[' + station + '] indicator connection closed, retrying in 3s...');
    latest[station].connected = false;
    broadcast({ type: 'status', station, connected: false });
    setTimeout(() => connectIndicator(station), 3000);
  });
}

function parseLine(station, line) {
  const matches = line.match(weightRegex);
  if (!matches || matches.length === 0) return;
  const value = parseFloat(matches[matches.length - 1]);
  if (Number.isNaN(value)) return;

  let stable = null;
  if (cfg.stableToken && line.indexOf(cfg.stableToken) !== -1) stable = true;
  else if (cfg.unstableToken && line.indexOf(cfg.unstableToken) !== -1) stable = false;

  latest[station] = { value, stable, raw: line, ts: Date.now(), connected: true };
  broadcast({ type: 'weight', station, ...latest[station] });
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
    res.end(JSON.stringify({ ok: true, stations: latest }));
    return;
  }

  // /camera/in/top, /camera/in/side, /camera/out/top, /camera/out/side
  const camMatch = pathname.match(/^\/camera\/(in|out)\/(top|side)$/);
  if (camMatch) {
    const [, station, side] = camMatch;
    const stCfg = cfg.stations[station];
    const camUrl = side === 'top' ? stCfg.topCameraSnapshotUrl : stCfg.sideCameraSnapshotUrl;
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
  for (const st of STATIONS) ws.send(JSON.stringify({ type: 'weight', station: st, ...latest[st] }));
  ws.on('close', () => wsClients.delete(ws));
});

server.listen(cfg.httpPort, () => {
  console.log('Weighbridge bridge running on http://localhost:' + cfg.httpPort);
  console.log('  Live weight: ws://localhost:' + cfg.httpPort);
  for (const st of STATIONS) {
    console.log('  [' + st + '] cameras: http://localhost:' + cfg.httpPort + '/camera/' + st + '/top , /camera/' + st + '/side');
  }
});

for (const st of STATIONS) connectIndicator(st);

/*
README — Weighbridge Bridge Setup
==================================
Ye bridge weighbridge.html aur real hardware (IN + OUT indicator, aur unke
CCTV) ke beech mein chalta hai, kyunki browser seedha raw TCP socket ya
password-protected cross-network camera se baat nahi kar sakta.

1. PC par Node.js install karo (v18+): https://nodejs.org
2. is 'bridge' folder me terminal khol ke:
     npm install
3. 'bridge-config.json' edit karo:
     - stations.in / stations.out: har weighbridge point (entry/exit) ke
       indicator ka LAN IP + TCP port, aur uske top/side camera snapshot
       URL (jaise http://192.168.0.86/snapshot.jpg).
     - cameraUser/cameraPassword: agar cameras login maangte hain (sab
       cameras same login use karte hain to yahin ek jagah daal do).
     - weightRegex: indicator jo text bhejta hai usme se number nikalne
       ka pattern. Default kaam kar jaata hai agar sirf number aata hai.
4. Chalao:
     node server.js
   "Weighbridge bridge running..." aur dono stations ke "connected"
   messages dikhne chahiye.
5. weighbridge.html kholo, Settings tab me "Bridge Address" me
   http://localhost:8090 confirm karo, fir Weighment tab me
   "Connect Indicator" dabao — IN weight/camera pehle weighment ke liye,
   OUT weight/camera doosre weighment ke liye automatically use honge.

Agar bridge PC (jaha browser chal raha hai) se alag machine par chala
rahe ho, to Bridge Address me us machine ka IP daalo
(jaise http://192.168.0.50:8090) — indicator/camera IPs bridge ke
config me hi rehte hain, browser me nahi.
*/
