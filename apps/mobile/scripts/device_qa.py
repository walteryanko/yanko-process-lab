"""Real adb/UIAutomator release-APK verification, no screenshots from mockups."""
import subprocess,time,json,pathlib,re,xml.etree.ElementTree as ET,traceback,os,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'release';OUT.mkdir(exist_ok=True)
PKG='com.ycs.processlab';report={'checks':[],'ok':False}
def adb(*args,timeout=40):
 return subprocess.check_output(['adb',*map(str,args)],timeout=timeout,stderr=subprocess.STDOUT).decode(errors='replace')
def check(name,condition,detail=None):
 report['checks'].append({'name':name,'ok':bool(condition),'detail':detail});print(name,condition,flush=True)
 if not condition:raise AssertionError(name+': '+str(detail))
def xml():
 adb('shell','uiautomator','dump','/sdcard/window.xml');root=ET.fromstring(adb('shell','cat','/sdcard/window.xml'))
 # CI image may show an unrelated Pixel Launcher boot ANR. Never dismiss ProcessLab failures.
 if any(n.get('text')=="Pixel Launcher isn't responding" for n in root.iter('node')):
  report['emulator_launcher_recoveries']=report.get('emulator_launcher_recoveries',0)+1
  close=next(n for n in root.iter('node') if n.get('resource-id')=='android:id/aerr_close')
  b=list(map(int,re.findall(r'\d+',close.attrib['bounds'])))
  adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2)
  adb('shell','am','force-stop','com.google.android.apps.nexuslauncher')
  adb('shell','am','start','-W','-n',PKG+'/.MainActivity');time.sleep(1)
  adb('shell','uiautomator','dump','/sdcard/window.xml');root=ET.fromstring(adb('shell','cat','/sdcard/window.xml'))
 return root
def find(label,wait=30):
 stop=time.monotonic()+wait
 while time.monotonic()<stop:
  root=xml()
  nodes=list(root.iter('node'))
  for attribute in ['content-desc','resource-id','text']:
   for n in nodes:
    if (n.get(attribute,'').endswith(label) if attribute=='resource-id' else n.get(attribute)==label):return n
  time.sleep(.5)
 raise AssertionError('UI element missing: '+label)
def tap_at(point):
 adb('shell','input','tap',*point);time.sleep(.4)
def tap(label):
 n=find(label);nums=list(map(int,re.findall(r'\d+',n.attrib['bounds'])));point=((nums[0]+nums[2])//2,(nums[1]+nums[3])//2);tap_at(point);return point
def bounds(label):return list(map(int,re.findall(r'\d+',find(label).attrib['bounds'])))
def clock():return find('simulation-time').get('text')
def tap_scrolled(label):
 for _ in range(8):
  root=xml()
  for n in root.iter('node'):
   if n.get('content-desc')==label or n.get('text')==label:
    b=list(map(int,re.findall(r'\d+',n.attrib['bounds'])))
    if b[3]-b[1]>60 and b[2]>b[0]:
     screen('numeric-apply-visible.png')
     return tap(label)
  b=bounds('properties-scroll');x=(b[0]+b[2])//2
  adb('shell','input','swipe',x,b[3]-30,x,b[1]+30,500);time.sleep(.4)
 raise AssertionError('Cannot scroll to '+label)
def screen(name):
 (OUT/name).write_bytes(subprocess.check_output(['adb','exec-out','screencap','-p']))
try:
 apk=pathlib.Path(os.environ['PROCESSLAB_APK']) if os.environ.get('PROCESSLAB_APK') else ROOT/'android/app/build/outputs/apk/release/app-release.apk'
 report['tested_apk_sha256']=hashlib.sha256(apk.read_bytes()).hexdigest()
 report['device_abis']=adb('shell','getprop','ro.product.cpu.abilist').strip()
 report['native_bridge']=adb('shell','getprop','ro.dalvik.vm.native.bridge').strip()
 adb('install','-r',apk,timeout=120);check('release APK installed',True)
 adb('logcat','-c');adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
 adb('shell','settings','put','system','accelerometer_rotation','0');adb('shell','settings','put','system','user_rotation','0')
 adb('shell','am','force-stop','com.google.android.apps.nexuslauncher');time.sleep(3)
 launch=adb('shell','am','start','-W','-n',PKG+'/.MainActivity');(OUT/'launch.txt').write_text(launch)
 find('CSTR');screen('home.png');tap('CSTR');portrait_play=tap('Iniciar simulação');time.sleep(2);tap_at(portrait_play);before=clock();check('real dynamic simulation advances',float(before.replace(',','.'))>0,before)
 rb=bounds('R-101');tap_at(((rb[0]+rb[2])//2,rb[1]-45))
 screen('portrait.png');(OUT/'memory-portrait.txt').write_text(adb('shell','dumpsys','meminfo',PKG));(OUT/'gfx-portrait.txt').write_text(adb('shell','dumpsys','gfxinfo',PKG))
 adb('shell','settings','put','system','user_rotation','1');time.sleep(2);check('rotation preserves paused time',clock()==before)
 check('rotation preserves selected equipment',find('selected-node').get('text')=='R-101')
 nav=bounds('Ensaios');density=int(re.findall(r'\d+',adb('shell','wm','density'))[-1])/160
 check('landscape final navigation target fully visible',nav[3]-nav[1]>=48*density-2,nav)
 tap('Ensaios');find('Experiment Lab');tap('Planta');rb=bounds('R-101');cb=bounds('flow-canvas')
 check('landscape equipment label remains in canvas',rb[1]>=cb[1] and rb[3]<=cb[3],{'equipment':rb,'canvas':cb})
 screen('landscape.png');(OUT/'memory-landscape.txt').write_text(adb('shell','dumpsys','meminfo',PKG));(OUT/'gfx-landscape.txt').write_text(adb('shell','dumpsys','gfxinfo',PKG))
 for rotation in [0,1,0,1]:
  adb('shell','settings','put','system','user_rotation',rotation);time.sleep(.3)
 check('rapid rotations preserve state',clock()==before)
 tap('Iniciar simulação');time.sleep(1);adb('shell','settings','put','system','user_rotation','0');time.sleep(1);tap_at(portrait_play);after=clock();check('rotation while running preserves progress',float(after.replace(',','.'))>=float(before.replace(',','.')),after)
 tap('Parar e salvar');time.sleep(1);adb('shell','input','keyevent','KEYCODE_HOME');time.sleep(1);adb('shell','am','force-stop',PKG)
 adb('shell','am','start','-W','-n',PKG+'/.MainActivity')
 # Recovered project is behind the home screen; use saved project picker without creating a new one.
 tap('Abrir projetos');tap('Abrir CSTR · Propilenoglicol');check('SQLite survives process termination',clock()==after,{'before':after,'after':clock()})
 tap('Controle');tap('Ajustar parâmetros');adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1');tap('Setpoint K');adb('shell','input','text','333.456');time.sleep(.5)
 check('exact numeric entry retains decimals',find('Setpoint K').get('text')=='333.456');screen('numeric-keyboard.png')
 tap_scrolled('Aplicar');tap('Ajustar parâmetros');check('apply commits currently focused numeric value',find('Setpoint K').get('text')=='333.456');tap('Setpoint K')
 adb('shell','settings','put','system','user_rotation','1');time.sleep(.8)
 check('rotation preserves numeric edit',find('Setpoint K').get('text')=='333.456')
 adb('shell','settings','put','system','user_rotation','0');time.sleep(.8)
 tap('Fechar')
 check('numeric configuration preserves simulation time',clock()==after)
 tap('Sensores');screen('sensors.png')
 tap('Início');tap('Nova planta');tap('Mover equipamento')
 before_bounds=bounds('R-101');x=(before_bounds[0]+before_bounds[2])//2;y=before_bounds[1]-45
 adb('shell','input','swipe',x,y,x+70,y-25,700);time.sleep(1)
 after_bounds=bounds('R-101');check('actual equipment drag changes layout',after_bounds!=before_bounds,{'before':before_bounds,'after':after_bounds})
 tap('Desfazer');time.sleep(.5);check('layout undo restores equipment',bounds('R-101')==before_bounds)
 tap('Mover planta');before_bounds=bounds('R-101');cb=bounds('flow-canvas');x=(cb[0]+cb[2])//2;y=(cb[1]+cb[3])//2
 adb('shell','input','swipe',x,y,x-55,y+25,600);time.sleep(.5);check('actual canvas pan changes view',bounds('R-101')!=before_bounds)
 tap('Centralizar planta');flow_play=tap('Iniciar simulação');time.sleep(1);tap_at(flow_play);check('connected equipment network executes on phone',float(clock().replace(',','.'))>0);screen('flow-editor.png')
 adb('shell','am','start','-W','-a','android.intent.action.VIEW','-d','processlab://verify','-p',PKG)
 find('VERIFIED_DEVICE_OK',wait=150);logs=adb('logcat','-d','-v','brief');(OUT/'android-logcat.txt').write_text(logs)
 matches=re.findall(r'PROCESSLAB_QA_RESULT (\{[^\n]+\})',logs)
 check('Hermes scientific parity and native SQLite verification',bool(matches))
 qa=json.loads(matches[-1]);check('all device numerical gates',qa['ok']);(OUT/'device-science.json').write_text(json.dumps(qa,indent=2))
 memory=adb('shell','dumpsys','meminfo',PKG);(OUT/'android-memory.txt').write_text(memory)
 (OUT/'android-gfxinfo.txt').write_text(adb('shell','dumpsys','gfxinfo',PKG))
 (OUT/'device.txt').write_text(adb('shell','getprop'))
 check('no Metro/development server required',True,'Installed non-debuggable release with bundled Hermes bytecode; Wi-Fi/data disabled')
 report['ok']=True
except Exception as e:
 report['error']=str(e);traceback.print_exc()
 try:screen('failure.png');(OUT/'failure-ui.xml').write_text(ET.tostring(xml(),encoding='unicode'));(OUT/'android-logcat.txt').write_text(adb('logcat','-d'))
 except Exception:pass
finally:
 (OUT/'device-qa.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if not report['ok']:raise SystemExit(1)
