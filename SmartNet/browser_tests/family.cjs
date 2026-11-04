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
    assert.equal(await page.getByText('Demanda / referencia',{exact:true}).isVisible(),false);
    assert.equal(await page.getByText('⚪ Falta un dato',{exact:false}).isVisible(),true);
    await headline.scrollIntoViewIfNeeded();
    await page.screenshot({path:'/tmp/smartnet-family-results.png'});
    await page.getByText('Probar dejar las descargas para después',{exact:true}).click();
    await page.getByText('Todo queda igual: las ideas elegidas no afectan las actividades que agregaste.',{exact:true}).waitFor();
    await numbers.click();
    await page.getByText('Demanda / referencia',{exact:true}).waitFor({state:'visible'});
    await page.setViewportSize({width:390,height:844});
    await headline.scrollIntoViewIfNeeded();
    await page.screenshot({path:'/tmp/smartnet-family-mobile.png'});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
    console.log('Family results: summary, missing data, collapsed numbers, no-effect scenario, mobile width passed');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
