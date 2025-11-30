const CACHE='berries-cache-v1';const OFFLINE_URL='/static/offline.html';
const ASSETS=['/','/harvests/new','/harvests','/reports','/weekly','/login',OFFLINE_URL,
'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'];
const DB_NAME='berries-db';const DB_VERSION=1;const STORE='pending-harvests';
function idbOpen(){return new Promise((res,rej)=>{const r=indexedDB.open(DB_NAME,DB_VERSION);r.onupgradeneeded=e=>{const db=e.target.result;if(!db.objectStoreNames.contains(STORE))db.createObjectStore(STORE,{keyPath:'temp_id'});};r.onsuccess=e=>res(e.target.result);r.onerror=e=>rej(e.target.error);});}
async function idbGetAll(){const db=await idbOpen();return new Promise((res,rej)=>{const tx=db.transaction(STORE,'readonly');const rq=tx.objectStore(STORE).getAll();rq.onsuccess=()=>res(rq.result||[]);rq.onerror=e=>rej(e.target.error);});}
async function idbClear(items){const db=await idbOpen();return new Promise((res,rej)=>{const tx=db.transaction(STORE,'readwrite');const st=tx.objectStore(STORE);for(const it of items)st.delete(it.temp_id);tx.oncomplete=()=>res(true);tx.onerror=e=>rej(e.target.error);});}
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim())});
self.addEventListener('fetch',e=>{const req=e.request;if(req.method!=='GET')return;e.respondWith(fetch(req).then(res=>{const copy=res.clone();caches.open(CACHE).then(c=>c.put(req,copy));return res;}).catch(()=>caches.match(req).then(r=>r||caches.match(OFFLINE_URL))))});
async function syncHarvests(){const items=await idbGetAll();if(!items.length)return;const res=await fetch('/api/harvests/bulk',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({items})});if(res.ok){const data=await res.json();if(data.ok)await idbClear(items);}}
self.addEventListener('sync',e=>{if(e.tag==='sync-harvests'){e.waitUntil(syncHarvests())}});
self.addEventListener('message',e=>{if(e.data&&e.data.type==='SYNC_NOW'){e.waitUntil(syncHarvests())}});
