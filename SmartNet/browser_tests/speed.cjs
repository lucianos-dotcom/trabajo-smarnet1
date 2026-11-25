/* Run with a local Streamlit server on port 8501 and Playwright + Chromium.
   This test uses controlled network responses, never claims a live speed result. */
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  try {
    const page=await browser.newPage({viewport:{width:1360,height:1000}});
    let bytes=0, requests=0, mode='success';
    await page.route('https://speed.cloudflare.com/**',async route=>{
      requests++;
      if(mode==='failure') return route.abort('failed');
      if(mode==='slow') {
        await new Promise(r=>setTimeout(r,500));
      }
      const request=route.request();
      const url=new URL(request.url());
      const size=Number(url.searchParams.get('bytes')||0);
      const body=request.postDataBuffer();
      bytes+=size+(body?.length||0);
      await new Promise(r=>setTimeout(r,40));
      await route.fulfill({status:200,headers:{'Access-Control-Allow-Origin':'*','Content-Type':'application/octet-stream','Cache-Control':'no-store'},body:Buffer.alloc(size)});
    });
    await page.goto('http://127.0.0.1:8501');
    await page.getByRole('heading',{name:'SmartNet · ¿Alcanza tu internet para todos?'}).waitFor();
    await page.locator('iframe[src*="smartnet_speed"]').waitFor({timeout:30000});
    await page.waitForFunction(() => [...document.querySelectorAll('iframe')].some(f => f.src.includes('smartnet_speed') && f.contentDocument?.readyState === 'complete'));
    const component=page.frames().find(f=>f.url().includes('smartnet_speed'));
    assert(component,'Speed component must load');
    await component.getByRole('button',{name:'Medir mi conexión ahora'}).click();
    await component.getByText('Prueba completa:',{exact:false}).waitFor({timeout:30000});
    const chart=page.getByRole('img',{name:/^Descarga: .* Mbps · Subida: .* Mbps$/});
    await chart.waitFor();
    const iframe=page.locator('iframe[src*="smartnet_speed"]');
    assert((await chart.boundingBox()).y < (await iframe.boundingBox()).y);
    const chartLabel=await chart.getAttribute('aria-label');
    await page.getByText(/^Tiempo de respuesta: .* ms$/).waitFor();
    await page.getByText('Esta medición se usa automáticamente en la prueba.',{exact:true}).waitFor();
    assert.equal(await page.getByText('¿Cuántos megas tiene tu plan?',{exact:true}).count(),0);
    const measured=Number(chartLabel.match(/Descarga: ([^ ]+)/)[1].replace(',','.'));
    assert(measured>0);
    await page.getByRole('button',{name:'Siguiente →',exact:true}).click();
    await page.getByRole('button',{name:'Ver resultado →',exact:true}).click();
    await page.getByText('Detalle y números',{exact:true}).last().click();
    await page.getByText('Referencia: Medición del test de SmartNet.',{exact:true}).waitFor();
    const context=page.locator('.st-key-slide_context');
    const reference=Number((await context.innerText()).match(/([0-9.]+) Mbps de descarga/)[1]);
    assert(Math.abs(reference-measured)<0.11);
    await page.getByRole('button',{name:'← Atrás',exact:true}).click();
    await page.getByText('Pantalla 2 de 3',{exact:true}).waitFor();
    await page.getByRole('button',{name:'← Atrás',exact:true}).click();
    await chart.waitFor();
    assert(bytes<45000000,`Bounded data use: ${bytes}`);
    // After six warm-up and latency requests, each direction can take one to four transfers.
    assert(requests >= 8 && requests <= 14, `Unexpected request count: ${requests}`);
    mode='failure';
    await component.getByRole('button',{name:'Medir mi conexión ahora'}).click();
    await component.getByText('No se pudo completar la prueba',{exact:false}).waitFor();
    assert.equal(await chart.getAttribute('aria-label'),chartLabel);
    await page.getByText('Usar datos de mi plan o ingresarlos a mano',{exact:true}).click();
    await page.getByText('Prueba con datos ingresados a mano.',{exact:true}).waitFor();
    await page.getByText('Usar datos de mi plan o ingresarlos a mano',{exact:true}).click();
    await page.getByText('Esta medición se usa automáticamente en la prueba.',{exact:true}).waitFor();
    mode='slow';
    await component.getByRole('button',{name:'Medir mi conexión ahora'}).click();
    await component.getByRole('button',{name:'Cancelar',exact:true}).click();
    await component.getByText('No se pudo completar la prueba',{exact:false}).waitFor();
    await page.screenshot({path:'/tmp/smartnet-browser.png',fullPage:true});
    console.log(JSON.stringify({controlled_speed_flow:'passed',error_flow:'passed',cancel_flow:'passed',bytes,requests,measured}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
