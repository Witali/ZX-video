// Loopback-only review server. No upload or publication capability.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(process.argv[2]);
const port = Number(process.argv[3] || 4196);
const film = process.argv[4] || 'Expedition-33-ZX-Spectrum-Demo.mp4';
const timeline = JSON.parse(fs.readFileSync(path.join(root, 'materials/work/timeline.json')));
const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scenes = timeline.scenes.filter(s => s.id !== 'loading');
const names = {opening:'Заставка',lumiere:'Lumière',alicia:'Alicia',ending:'Финал'};
const html = `<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Expedition 33 — просмотр ролика</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1119;color:#eee6d7;font:16px system-ui,sans-serif}
main{max-width:1160px;margin:32px auto;padding:0 24px}header{display:flex;align-items:baseline;justify-content:space-between;gap:20px}
h1{font-size:27px;font-weight:550;margin:0 0 8px}p{color:#a8b2c0;line-height:1.6;margin:8px 0 20px}.badge{color:#e2c689;font-size:14px;white-space:nowrap}
video{display:block;width:100%;aspect-ratio:16/9;background:black;border:1px solid #303946;border-radius:8px}
nav{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 22px}button,a.button{font:inherit;color:#eee6d7;border:1px solid #465166;background:#171f2c;border-radius:6px;padding:9px 16px;cursor:pointer;text-decoration:none}
button:hover,a.button:hover{border-color:#e2c689}a{color:#d9c38f}details{border-top:1px solid #303946;padding-top:18px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui;color:#bdc7d4}
</style><main><header><h1>Expedition 33 Demo · ZX Spectrum</h1><span class="badge">Локальный просмотр · не опубликовано</span></header>
<p>Полный ролик с заставкой, Lumière и Alicia. 1920 × 1080 · 50 кадров/с · стерео.</p>
<video id="film" controls preload="metadata" poster="/thumbnail.png" src="/${film}"></video>
<nav>${scenes.map(s=>`<button data-time="${s.start}">${names[s.id]}</button>`).join('')}<a class="button" download href="/${film}">Скачать MP4</a></nav>
<details><summary>Описание для YouTube — со ссылкой на эмулятор</summary><pre>${escape(fs.readFileSync(path.join(root,'description.txt'),'utf8'))}</pre></details>
</main><script>const video=document.getElementById('film');for(const b of document.querySelectorAll('[data-time]'))b.addEventListener('click',()=>{video.currentTime=Number(b.dataset.time);video.pause()});const start=Number(new URLSearchParams(location.search).get('t')||0);if(start){const seek=()=>{video.currentTime=start};if(video.readyState)seek();else video.addEventListener('loadedmetadata',seek,{once:true})}</script></html>`;
const allowed = new Map([['/'+film,[film,'video/mp4']],['/thumbnail.png',['thumbnail.png','image/png']],['/description.txt',['description.txt','text/plain; charset=utf-8']]]);
http.createServer((req,res)=>{
  const pathname=new URL(req.url,'http://127.0.0.1').pathname;
  if(pathname==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(html);return}
  if(pathname==='/favicon.ico'){res.writeHead(204);res.end();return}
  const entry=allowed.get(pathname);
  if(!entry){res.writeHead(404);res.end();return}
  const file=path.join(root,entry[0]),size=fs.statSync(file).size;
  const range=req.headers.range?.match(/^bytes=(\d+)-(\d*)$/);
  const common={'Content-Type':entry[1],'Accept-Ranges':'bytes','Cache-Control':'no-store'};
  if(range){const start=Number(range[1]),end=Math.min(range[2]?Number(range[2]):size-1,size-1);
    if(start>end){res.writeHead(416,{'Content-Range':`bytes */${size}`});res.end();return}
    res.writeHead(206,{...common,'Content-Range':`bytes ${start}-${end}/${size}`,'Content-Length':end-start+1});
    if(req.method==='HEAD')res.end();else fs.createReadStream(file,{start,end}).pipe(res);
  }else{res.writeHead(200,{...common,'Content-Length':size});if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res)}
}).listen(port,'127.0.0.1',()=>console.log(`Review only: http://127.0.0.1:${port}/`));
