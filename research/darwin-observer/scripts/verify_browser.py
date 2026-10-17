"""Local UI verification, actual backend execution and offline rendering."""
import json,sys,threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from darwin.dashboard import app
root=Path(__file__).resolve().parents[1]
server=make_server('127.0.0.1',8876,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
errors=[];checks=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=sys.argv[1],headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--use-gl=disabled','--use-angle=disabled'])
  page=browser.new_page(viewport={'width':1440,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8876');page.wait_for_selector('#traj');checks.append('initial data and canvas')
  page.screenshot(path=str(root.parent/'dashboard-desktop.png'),full_page=True)
  page.locator('#time').fill('90');page.locator('#time').dispatch_event('input');assert page.locator('#clock').inner_text()=='1.35 h';checks.append('playhead updates twin')
  for tab in ['arena','engine','timeline','benchmark','equation']:
   page.locator(f'[data-tab="{tab}"]').click();assert page.locator('#content').inner_text();checks.append('panel '+tab)
  assert page.locator('math').count()>=2
  with page.expect_download() as dl:page.locator('#latex').click()
  assert dl.value.suggested_filename.endswith('.tex');checks.append('LaTeX export')
  page.locator('[data-tab="engine"]').click();page.locator('[data-hyp="H0"]').click();assert page.locator('.panel h2').last.inner_text()=='H0';checks.append('hypothesis inspection')
  page.locator('[data-tab="twin"]').click();page.locator('#seed').fill('654321');page.locator('#run').click();page.wait_for_function('document.querySelector(".chip").textContent.includes("654321")',timeout=60000);checks.append('new real simulation')
  page.locator('#scenario').select_option('D_legacy');assert 'histórica' in page.locator('#scenario').inner_text();checks.append('scenario change')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(root.parent/'dashboard-mobile.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2');checks.append('mobile no horizontal overflow')
  offline=root/'Laboratorio_Darwin_Observer.html'
  if offline.exists():
   page.goto(offline.as_uri());page.wait_for_selector('#traj');assert page.locator('#run').is_disabled();checks.append('offline honest backend state')
  browser.close()
finally:server.shutdown()
out=dict(checks=checks,page_errors=errors,passed=not errors)
(root/'artifacts'/'browser_verification.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out));assert not errors
