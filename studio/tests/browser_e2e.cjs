// Browser -> authenticated Python API -> numerical graph -> save/reopen.
const {chromium}=require('../ui/node_modules/playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');const os=require('node:os');
const assert=require('node:assert/strict');
async function main(){
  const repo=path.resolve(__dirname,'../..');const data=fs.mkdtempSync(path.join(os.tmpdir(),'processlab-browser-'));
  const proc=spawn(process.env.PYTHON||'python3',['studio/desktop.py','--browser','--data-dir',data],{cwd:repo,env:{...process.env,PYTHONPATH:'studio',OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'},stdio:['ignore','pipe','pipe']});
  let log='';proc.stderr.on('data',b=>{log+=b;});
  let browser;
  try{
    const url=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(Error('Python host startup timeout: '+log)),30000);proc.stdout.on('data',b=>{output+=b;const match=output.match(/http:\/\/127\.0\.0\.1:\d+\/#token=\S+/);if(match){clearTimeout(timer);resolve(match[0]);}});proc.on('exit',code=>reject(Error('Host exited '+code+': '+log)));});
    browser=await chromium.launch({headless:true,args:['--no-sandbox'],...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});
    const page=await browser.newPage({viewport:{width:1440,height:980}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.goto(url);await page.waitForSelector('[data-testid="studio-ready"]');
    await page.getByTitle('Adicionar Aquecedor; arraste para posicionar').click();
    assert.equal(await page.locator('.react-flow__node').count(),4);
    await page.getByTitle('Desfazer',{exact:true}).click();
    assert.equal(await page.locator('.react-flow__node').count(),3);
    const tank=page.locator('.react-flow__node[data-id="T-101"]');const before=await tank.boundingBox();
    await page.mouse.move(before.x+before.width/2,before.y+before.height/2);await page.mouse.down();
    await page.mouse.move(before.x+before.width/2+45,before.y+before.height/2-25,{steps:8});await page.mouse.up();
    const moved=await tank.boundingBox();assert.ok(moved.x>before.x+30,'Equipment dragging must persist its layout');
    await page.getByRole('button',{name:'Executar',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('.runtime-clock b').textContent.replaceAll('.','').replace(',','.'))>=20);
    await page.getByRole('button',{name:'Pausar',exact:true}).click();
    await page.waitForTimeout(350);const paused=await page.locator('.runtime-clock b').innerText();await page.waitForTimeout(350);assert.equal(await page.locator('.runtime-clock b').innerText(),paused);
    await page.getByRole('button',{name:'Salvar',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.statusbar').textContent.includes('Projeto salvo'));
    await page.getByRole('button',{name:'Regime permanente',exact:true}).click();await page.getByText('Resultado do cálculo',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Controle',exact:true}).last().click();await page.getByLabel('Controlador',{exact:true}).selectOption('manual');
    await page.getByRole('button',{name:'Sensores virtuais',exact:true}).click();await page.getByLabel('Estimador',{exact:true}).selectOption('ukf');
    await page.getByRole('button',{name:'Fluxograma',exact:true}).click();await page.getByRole('button',{name:'Restaurar estado inicial'}).click();
    await page.getByRole('button',{name:'Salvar',exact:true}).click();await page.waitForTimeout(300);
    await page.getByRole('button',{name:/Propilenoglicol/}).click();await page.getByText('CSTR · PG',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Executar',exact:true}).click();await page.waitForFunction(()=>Number(document.querySelector('.runtime-clock b').textContent.replaceAll('.','').replace(',','.'))>=108);
    await page.getByRole('button',{name:'Pausar',exact:true}).click();await page.waitForTimeout(300);
    await page.getByLabel('Abrir projeto salvo').selectOption('heated-tank');await page.waitForFunction(()=>document.querySelector('.project-name').value.includes('Tanque'));
    await page.getByRole('button',{name:'Controle',exact:true}).last().click();assert.equal(await page.getByLabel('Controlador',{exact:true}).inputValue(),'manual');
    await page.getByRole('button',{name:'Fluxograma',exact:true}).click();await page.screenshot({path:process.env.PROCESSLAB_SCREENSHOT||'/tmp/processlab-tested.png',fullPage:true});
    await page.setViewportSize({width:1100,height:768});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);
    const evidence={ok:true,checks:['real backend startup','equipment insertion and undo','equipment drag','dynamic temperature/clock','pause stability','native project persistence','steady solve','controller configuration','observer configuration','PG adapter execution','saved project round trip','1100px layout'],page_errors:errors,browser:await browser.version(),platform:process.platform};
    fs.mkdirSync(path.join(repo,'studio/evidence'),{recursive:true});fs.writeFileSync(path.join(repo,'studio/evidence/browser-e2e.json'),JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
  }finally{if(browser)await browser.close();proc.kill();fs.rmSync(data,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
