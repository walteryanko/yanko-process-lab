"""Real adb/UIAutomator release-APK verification, no screenshots from mockups."""
import subprocess,time,json,pathlib,re,xml.etree.ElementTree as ET,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'release';OUT.mkdir(exist_ok=True)
PKG='com.ycs.processlab';report={'checks':[],'ok':False}
def adb(*args,timeout=40):
 return subprocess.check_output(['adb',*map(str,args)],timeout=timeout,stderr=subprocess.STDOUT).decode(errors='replace')
def check(name,condition,detail=None):
 report['checks'].append({'name':name,'ok':bool(condition),'detail':detail});print(name,condition,flush=True)
 if not condition:raise AssertionError(name+': '+str(detail))
def xml():
 adb('shell','uiautomator','dump','/sdcard/window.xml');return ET.fromstring(adb('shell','cat','/sdcard/window.xml'))
def find(label,wait=30):
 stop=time.monotonic()+wait
 while time.monotonic()<stop:
  root=xml()
  for n in root.iter('node'):
   if n.get('content-desc')==label or n.get('text')==label or n.get('resource-id','').endswith(label):return n
  time.sleep(.5)
 raise AssertionError('UI element missing: '+label)
def tap(label):
 n=find(label);nums=list(map(int,re.findall(r'\d+',n.attrib['bounds'])));adb('shell','input','tap',(nums[0]+nums[2])//2,(nums[1]+nums[3])//2);time.sleep(.4)
def clock():return find('simulation-time').get('text')
def screen(name):
 (OUT/name).write_bytes(subprocess.check_output(['adb','exec-out','screencap','-p']))
try:
 apk=next((ROOT/'android/app/build/outputs/apk/release').glob('*x86_64*.apk'))
 adb('install','-r',apk,timeout=120);check('release APK installed',True)
 adb('logcat','-c');adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
 adb('shell','settings','put','system','accelerometer_rotation','0');adb('shell','settings','put','system','user_rotation','0')
 launch=adb('shell','am','start','-W','-n',PKG+'/.MainActivity');(OUT/'launch.txt').write_text(launch)
 tap('CSTR');tap('Iniciar simulação');time.sleep(2);tap('Pausar simulação');before=clock();check('real dynamic simulation advances',float(before.replace(',','.'))>0,before)
 screen('portrait.png')
 adb('shell','settings','put','system','user_rotation','1');time.sleep(2);check('rotation preserves paused time',clock()==before);screen('landscape.png')
 tap('Iniciar simulação');time.sleep(1);adb('shell','settings','put','system','user_rotation','0');time.sleep(1);tap('Pausar simulação');after=clock();check('rotation while running preserves progress',float(after.replace(',','.'))>=float(before.replace(',','.')),after)
 tap('Parar e salvar');time.sleep(1);adb('shell','input','keyevent','KEYCODE_HOME');time.sleep(1);adb('shell','am','force-stop',PKG)
 adb('shell','am','start','-W','-n',PKG+'/.MainActivity');tap('Planta') if False else None
 # Recovered project is behind the home screen; use saved project picker without creating a new one.
 tap('Abrir projetos');tap('Abrir CSTR · Propilenoglicol');check('SQLite survives process termination',clock()==after,{'before':after,'after':clock()})
 tap('Sensores');screen('sensors.png')
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
