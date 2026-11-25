/* Verify the familiar results view in an actual browser. No external test traffic. */
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  try {
    const page=await browser.newPage({viewport:{width:1360,height:1000}});
    await page.goto('http://127.0.0.1:8501');
    const headline=page.getByRole('heading',{name:'🏠 Vamos bien, pero falta una pista',exact:true});
    await headline.waitFor();
    const numbers=page.getByText('🔢 Quiero ver los números',{exact:true});
    await numbers.waitFor();
    assert.equal(await page.getByText('Uso estimado de descarga',{exact:true}).isVisible(),false);
    const upload=page.getByRole('heading',{name:'📷 Enviar videos y hacer llamadas',exact:true});
    assert.equal(await upload.isVisible(),false);
    await page.getByText('Ver detalle del resultado',{exact:true}).click();
    await upload.waitFor({state:'visible'});
    await headline.scrollIntoViewIfNeeded();
    await page.screenshot({path:'/tmp/smartnet-family-results.png'});
    await page.getByText('Probar dejar las descargas para después',{exact:true}).click();
    await page.getByText('Todo queda igual: las ideas elegidas no afectan las actividades que agregaste.',{exact:true}).waitFor();
    assert.equal(await page.getByText(/Matrices, bandas y funciones|Matriz de/).count(),0);
    await numbers.click();
    await page.getByText('Uso estimado de descarga',{exact:true}).waitFor({state:'visible'});
    await page.setViewportSize({width:390,height:844});
    await headline.scrollIntoViewIfNeeded();
    await page.screenshot({path:'/tmp/smartnet-family-mobile.png'});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
    console.log('Family results: summary, missing data, collapsed numbers, no-effect scenario, mobile width passed');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
