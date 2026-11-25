/* Run with Playwright and Chromium against local Streamlit or SMARTNET_URL. */
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const phone = '📱 Celular';
const pc = '💻 Notebook o PC';
const tv = '📺 Smart TV';
const consoleDevice = '🎮 Consola';
const camera = '📷 Cámara de seguridad';
const chat = 'WhatsApp y navegar';
const call = 'Videollamada o clase online';
const hd = 'Ver videos o series en HD';
const cloud = 'Cámara transmitiendo a la nube';
const unknown = 'No sé la banda';

const presets = {
  'Una tarde en casa': [
    [phone, chat, 2], [pc, call, 1], [tv, hd, 1], [consoleDevice, 'Jugar online', 1],
  ],
  'Todos viendo series': [[phone, hd, 2], [tv, 'Ver videos o series en 4K', 2]],
  'Descargas y clases online': [[pc, call, 2], [consoleDevice, 'Descargar juegos o archivos', 2], [tv, hd, 1]],
  'Ejemplo de la asignatura': [[phone, chat, 2], [phone, call, 1], [pc, chat, 1], [pc, call, 1], [tv, hd, 2]],
  'Casa con cámaras y dispositivos inteligentes': [
    [camera, cloud, 4], ['💡 Ampolleta o enchufe inteligente', 'Dispositivo inteligente en espera', 5],
    ['📺 TV Box / decodificador', hd, 1], ['🔊 Parlante inteligente', 'Escuchar música', 1],
  ],
  'Empezar desde cero': [],
};

async function verify(page) {
  const box = label => page.getByTestId('stSelectbox').filter({ hasText: label });
  const number = label => page.getByRole('spinbutton', { name: label, exact: true });
  const remove = page.getByRole('button', { name: 'Quitar este grupo', exact: true });
  const add = page.getByRole('button', { name: '＋ Agregar otro equipo', exact: true });
  const choose = async (label, option) => {
    await box(label).getByRole('combobox').click();
    await page.getByRole('option', { name: option, exact: true }).click();
  };
  const setNumber = async (label, value) => {
    await number(label).fill(String(value));
    await number(label).press('Enter');
  };
  const checkRows = async expected => {
    await page.waitForFunction(count => document.querySelectorAll('[class*="st-key-remove_"] button').length === count, expected.length);
    for (const [i, [device, activity, count, band = unknown]] of expected.entries()) {
      const n = i + 1;
      await box('Equipo ' + n).getByText(device, { exact: true }).waitFor();
      await box('Actividad ' + n).getByText(activity, { exact: true }).waitFor();
      await box('Conexión del grupo ' + n).getByText(band, { exact: true }).waitFor();
      await page.waitForFunction(({ n, count }) => document.querySelector('input[aria-label="Cantidad ' + n + '"]')?.value === String(count), { n, count });
    }
  };
  const metric = async (label, value) => {
    await page.getByTestId('stMetric').filter({ hasText: label }).getByText(value, { exact: true }).waitFor({ state: 'attached' });
  };
  const preset = 'Prueba un ejemplo o arma tu casa';
  const academic = 'Ejemplo de la asignatura';
  const cameras = 'Casa con cámaras y dispositivos inteligentes';

  await page.goto(process.env.SMARTNET_URL || 'http://127.0.0.1:8501');
  await page.getByRole('heading', { name: 'SmartNet · ¿Alcanza tu internet para todos?' }).waitFor();
  await checkRows(presets['Una tarde en casa']);
  const names = Object.keys(presets);
  for (const name of [...names.slice(1), ...names, names[0]]) {
    await choose(preset, name);
    await checkRows(presets[name]);
  }

  await choose(preset, academic);
  await checkRows(presets[academic]);
  await choose('¿Cuántos megas tiene tu plan?', '20 Mbps');
  await page.getByText('🔢 Quiero ver los números', { exact: true }).click();
  await metric('Demanda de descarga', '14.5 Mbps');
  await metric('Demanda / referencia', '72.5%');
  await choose('¿Cuántos megas tiene tu plan?', 'Ingresar otra velocidad');
  await setNumber('Descarga de referencia (Mbps)', 10);
  await metric('Demanda / referencia', '145.0%');

  await choose(preset, cameras);
  await checkRows(presets[cameras]);
  await page.getByText('Conozco mi velocidad de subida (o la obtuve en el test)', { exact: true }).click();
  await setNumber('Subida de referencia (Mbps)', 5);
  await page.getByText('8.25 Mbps', { exact: true }).waitFor({ state: 'attached' });
  await page.getByText('165.0%', { exact: true }).waitFor({ state: 'attached' });
  await choose('Conexión del grupo 2', 'Cable de red');
  await page.getByRole('button', { name: 'Asignar bandas automáticamente' }).click();
  const assigned = presets[cameras].map((row, i) =>
    [...row, ['2,4 GHz', 'Cable de red', '5 GHz', '2,4 GHz'][i]]);
  await checkRows(assigned);
  await page.getByText(/Ocupación estimada en 2,4 GHz: 10\.9%/, { exact: false }).waitFor({ state: 'attached' });
  await page.getByText(/Ocupación estimada en 5 GHz: 1\.7%/, { exact: false }).waitFor({ state: 'attached' });

  await add.click();
  await checkRows([...assigned, [phone, chat, 1]]);
  await choose('Equipo 5', camera);
  await choose('Conexión del grupo 5', '5 GHz');
  await setNumber('Cantidad 5', 7);
  await checkRows([[camera, cloud, 4, '2,4 GHz'], ...assigned.slice(1), [camera, cloud, 7, '5 GHz']]);
  await remove.nth(1).click();
  await checkRows([[camera, cloud, 4, '2,4 GHz'], ...assigned.slice(2), [camera, cloud, 7, '5 GHz']]);
  await remove.first().click();
  await checkRows([...assigned.slice(2), [camera, cloud, 7, '5 GHz']]);

  await choose(preset, 'Empezar desde cero');
  await checkRows([]);
  assert(await page.getByRole('button', { name: 'Asignar bandas automáticamente' }).isDisabled());
  await add.click();
  await checkRows([[phone, chat, 1]]);
  await remove.first().click();
  await checkRows([]);
  await choose(preset, academic);
  await checkRows(presets[academic]);
  await metric('Demanda / referencia', '145.0%');
  assert.equal(await page.getByTestId('stException').count(), 0);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox'],
  });
  try {
    for (const viewport of [{ width: 1360, height: 1000 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport, isMobile: viewport.width === 390, hasTouch: viewport.width === 390 });
      await verify(page);
      console.log(`Rows, camera upload, Wi-Fi and academic numbers passed at ${viewport.width} × ${viewport.height}`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
