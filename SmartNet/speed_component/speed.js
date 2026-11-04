/* Streamlit component protocol, no external JavaScript dependencies. */
const start = document.getElementById('start');
const cancel = document.getElementById('cancel');
const status = document.getElementById('status');
const send = (type, data = {}) => window.parent.postMessage({isStreamlitMessage:true, type, ...data}, '*');
let controller;
let testLocation = "Sin etiqueta";
const median = xs => [...xs].sort((a,b)=>a-b)[Math.floor(xs.length/2)];
async function transfer(bytes, upload=false) {
  const payload = upload ? new Uint8Array(bytes) : undefined;
  if (payload) { // Fresh random chunks avoid artificially compressible upload data.
    for (let i=0;i<payload.length;i+=65536) crypto.getRandomValues(payload.subarray(i,Math.min(i+65536,payload.length)));
  }
  const token = crypto.randomUUID();
  const url = `https://speed.cloudflare.com/${upload?'__up':'__down'}?${upload?'':'bytes='+bytes+'&'}r=${token}`;
  const requestController = new AbortController();
  const abort = () => requestController.abort();
  const parentSignal = controller.signal;
  if (parentSignal.aborted) throw new DOMException("Cancelled", "AbortError");
  parentSignal.addEventListener('abort',abort,{once:true});
  const timeout = setTimeout(abort,15000);
  const before = performance.now();
  try {
    const response = await fetch(url,{method:upload?'POST':'GET',body:payload,cache:'no-store',credentials:'omit',signal:requestController.signal});
    if (!response.ok) throw new Error('HTTP '+response.status);
    const data = await response.arrayBuffer();
    if (!upload && data.byteLength !== bytes) throw new Error('Respuesta incompleta');
    const ms = performance.now()-before;
    return {ms, mbps:bytes*8/(ms/1000)/1e6};
  } finally {
    clearTimeout(timeout);
    parentSignal.removeEventListener('abort',abort);
  }
}
start.onclick = async () => {
  start.disabled=true; cancel.hidden=false; controller=new AbortController();
  const location = testLocation;
  let deadline=setTimeout(()=>controller.abort(),75000);
  try {
    status.textContent='Preparando… evita otras descargas durante la prueba.';
    await transfer(1000); // Warm up connection; exclude TLS setup from latency samples.
    const latencies=[];
    for(let i=0;i<5;i++) latencies.push((await transfer(1000)).ms);
    const results={};
    for (const upload of [false,true]) {
      status.textContent=upload?'Midiendo subida…':'Midiendo descarga…';
      let size=250000, samples=[];
      // Bounded adaptive sequential transfers; conservative throughput includes HTTP overhead.
      for(let i=0;i<4;i++) {
        const sample=await transfer(size,upload);
        samples.push(sample);
        if(sample.ms>=2000) break;
        size=Math.min(size*4, upload?4000000:10000000);
      }
      const useful=samples.filter(s=>s.ms>=150);
      const chosen=useful.length?useful:samples.slice(-1);
      results[upload?'upload':'download']=median(chosen.map(s=>s.mbps));
    }
    const value={...results, location, latency:median(latencies), jitter:Math.max(...latencies)-Math.min(...latencies), timestamp:new Date().toISOString(), id:crypto.randomUUID()};
    if (![value.download,value.upload,value.latency,value.jitter].every(Number.isFinite) || value.download<=0 || value.upload<=0) throw new Error('Resultado inválido');
    status.textContent=`Prueba completa: descarga ${value.download.toFixed(1)} Mbps · subida ${value.upload.toFixed(1)} Mbps · respuesta HTTP ${value.latency.toFixed(0)} ms.`;
    send('streamlit:setComponentValue',{value,dataType:'json'});
  } catch(error) {
    status.textContent='No se pudo completar la prueba (cancelación, tiempo de espera o bloqueo de red). No se guardó una medición nueva. Puedes repetir o ingresar un test manualmente.';
  } finally {
    clearTimeout(deadline); start.disabled=false; cancel.hidden=true;
    send('streamlit:setFrameHeight',{height:210});
  }
};
cancel.onclick=()=>controller?.abort();
window.addEventListener('message',event=>{
  if(event.source!==window.parent) return;
  if(event.data.type==='streamlit:render') {
    testLocation = event.data.args?.location || 'Sin etiqueta';
    send('streamlit:setFrameHeight',{height:210});
  }
});
send('streamlit:componentReady',{apiVersion:1});
send('streamlit:setFrameHeight',{height:210});
