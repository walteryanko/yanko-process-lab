// Optional browser QA. Requires Playwright and a local Chromium executable.
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..');
const playwright=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const executablePath=process.env.LAB_CHROMIUM;
 const browser=await playwright.chromium.launch({headless:true,executablePath,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+root+'/web/index.html');
 await page.waitForFunction(()=>window.LAB_UI);
 const panels=['reactor','probability','transport','arena','multiverse','benchmarks','control'];
 const snapshots=[];
 for(const name of panels){await page.locator('[data-view="'+name+'"]').click();snapshots.push({name,visible:await page.locator('#view-'+name).isVisible(),canvases:await page.locator('#view-'+name+' canvas').count()})}
 if(await page.locator('#control-table tbody tr,#control-table table tr').count()<5)throw Error('Control campaign missing from UI');
 if(await page.locator('#scenario option').count()!==8)throw Error('Expected eight real recorded scenarios');
 await page.locator('[data-view="probability"]').click();await page.locator('#dimension').click();
 await page.locator('#axis-x').selectOption('2');await page.locator('#axis-y').selectOption('4');
 await page.locator('#method').selectOption('M3');await page.locator('#time').fill('12');
 await page.locator('#scenario').selectOption('ambiguous');
 const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;await download.saveAs(path.join(root,'results','ui_export.json'));
 const exported=JSON.parse(fs.readFileSync(path.join(root,'results','ui_export.json'),'utf8'));
 if(exported.scenario!=='ambiguous'||!exported.data.M4)throw Error('Export is not current real data');
 fs.unlinkSync(path.join(root,'results','ui_export.json'));
 await page.setViewportSize({width:390,height:844});await page.locator('[data-view="reactor"]').click();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
 await page.screenshot({path:path.join(root,'..','ui-mobile.png'),fullPage:true});
 // Same-process test server works even in isolated execution network namespaces.
 const server=spawn(process.env.PYTHON||'python',['-m','schrodinger_lab.server','--no-browser','--port','8790'],{cwd:root,env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'}});
 let serverError='';server.stderr.on('data',x=>serverError+=x.toString());
 await new Promise((resolve,reject)=>{server.stdout.once('data',resolve);server.once('error',reject);server.once('exit',code=>reject(Error('Server exited '+code+' '+serverError)))});
 try{
  await page.goto('http://127.0.0.1:8790');await page.waitForFunction(()=>window.LAB_UI?.getState().online);
  const reportResponse=await page.request.get('http://127.0.0.1:8790/figures/01_rmse.png');
  if(!reportResponse.ok())throw Error('Scientific report figure unavailable through HTTP');
  await page.locator('#particles').selectOption('64');await page.locator('#seed').fill('4242');await page.locator('#run').click();
  await page.waitForFunction(()=>document.getElementById('job-status').textContent.includes('Nova execução concluída'),{timeout:120000});
  const generated=await page.evaluate(()=>window.LAB_UI.data.demos.gaussian.M4.result.seed);
  if(generated!==4242)throw Error('New simulation did not update UI');
  const checked={panels:snapshots,console_errors:errors,mobile_horizontal_overflow:overflow,export:'passed',live_engine_seed:generated};
  fs.writeFileSync(path.join(root,'results','ui_tests.json'),JSON.stringify(checked,null,2));console.log(checked);
 }finally{server.kill();await browser.close()}
 if(errors.length||overflow||snapshots.some(x=>!x.visible))process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
