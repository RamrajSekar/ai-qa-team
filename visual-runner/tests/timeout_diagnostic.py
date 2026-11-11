import sys,os,json,time,socket,threading,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'visual-runner'))
import httpx
from lab.runtime import WindowsProcessTree,BrowserLock,runner_environment
from lab.sample import serve
from lab.webdriver import DirectWebDriver
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--fresh',required=True);parser.add_argument('--cached',required=True);parser.add_argument('--driver',required=True)
parser.add_argument('--layers', nargs='+', choices=['direct','minimal','runner'], default=['direct','minimal','runner'])
parser.add_argument('--environment', choices=['inherited','filtered'], default='inherited')
parser.add_argument('--driver-log', choices=['file','pipe'], default='file')
options=parser.parse_args()
if options.environment=='filtered':
 filtered=runner_environment();os.environ.clear();os.environ.update(filtered)
folder=root/'tmp'/('timeout-study-'+uuid.uuid4().hex);folder.mkdir()
results=[]
driver=Path(options.driver)
browsers={'fresh':Path(options.fresh),'cached':Path(options.cached)}
lock=BrowserLock(root/'visual-runner/.runtime/browser.lock')
for layer in options.layers:
 for name,chrome in browsers.items():
  work=folder/(layer+'-'+name);work.mkdir();start=time.monotonic();events=[];tree=WindowsProcessTree();client=None;server=None;browser=None;stop=threading.Event()
  def event(stage,**kw): events.append({'seconds':round(time.monotonic()-start,3),'stage':stage,**kw})
  def watchdog():
   while not stop.wait(.1):
    if time.monotonic()-start > 65 or (work/'cancel').exists():
     tree.close();return
  threading.Thread(target=watchdog,daemon=True).start()
  env=runner_environment();env['CHROME_LOG_FILE']=str(work/'chrome.log')
  args=['--headless=new','--no-first-run','--no-default-browser-check','--enable-logging','--remote-debugging-port=0',f'--user-data-dir={work / "profile"}']
  try:
   if layer=='direct':
    event('launch');proc=tree.launch([str(chrome),*args,'about:blank'],env=env)
    end=time.monotonic()+45
    while time.monotonic()<end and proc.poll() is None and not (work/'profile/DevToolsActivePort').exists(): time.sleep(.1)
    event('observation',running=proc.poll() is None,exit_code=proc.poll(),devtools_file=(work/'profile/DevToolsActivePort').exists())
   elif layer=='minimal':
    with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    proc=tree.launch([str(driver),f'--port={port}','--allowed-ips=127.0.0.1','--verbose',f'--log-path={work / "driver.log"}'],env=env)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=httpx.Timeout(5,read=45),trust_env=False)
    end=time.monotonic()+6
    while True:
     try:
      if client.get('/status',timeout=.25).json()['value']['ready']:break
     except (httpx.HTTPError,ValueError,KeyError):pass
     if time.monotonic()>end:raise RuntimeError('driver_readiness')
     time.sleep(.1)
    event('driver_ready');event('post_session')
    response=client.post('/session',json={'capabilities':{'alwaysMatch':{'browserName':'chrome','goog:chromeOptions':{'binary':str(chrome),'args':args}}}})
    event('session_response',status=response.status_code,error=response.json().get('value',{}).get('error'),browser_version=response.json().get('value',{}).get('capabilities',{}).get('browserVersion'))
   else:
    server,url=serve();original=DirectWebDriver.call
    original_launch=WindowsProcessTree.launch
    def private_launch(self,args,**kwargs):
     if options.driver_log=='file' and Path(args[0]).resolve()==driver.resolve(): args=[*args,f'--log-path={work / "driver.log"}']
     return original_launch(self,args,**kwargs)
    WindowsProcessTree.launch=private_launch
    def call(self,method,path,payload=None):
     if path=='/session':
      global tree
      tree=self.tree
      payload['capabilities']['alwaysMatch']['goog:chromeOptions']['args']+=['--enable-logging',f'--log-file={work / "chrome.log"}']
      event('post_session')
     return original(self,method,path,payload)
    DirectWebDriver.call=call
    browser=DirectWebDriver(str(chrome),str(driver),url,False,work,lambda:None,lambda stage,reason=None:event(stage or 'reason',reason=reason),lambda value:event('snapshot',**value))
    event('session_created');DirectWebDriver.call=original
  except Exception as exc:event('error',exception=type(exc).__name__)
  finally:
   event('before_cleanup',browser_state=tree.browser_status(),devtools_file=(work/'profile/DevToolsActivePort').exists())
   event('cleanup_begin')
   if layer=='runner':
    DirectWebDriver.call=original
    WindowsProcessTree.launch=original_launch
   if browser:browser.close()
   tree.close();time.sleep(.2);event('cleanup_observation',browser_state=tree.browser_status());tree.release_observations()
   if client:client.close()
   if server:server.shutdown();server.server_close()
   stop.set()
   row={'environment':options.environment,'driver_log':options.driver_log,'layer':layer,'browser':name,'read_timeout_seconds':45,'events':events};results.append(row)
   (folder/'sanitized.json').write_text(json.dumps(results,indent=2));print(json.dumps(row),flush=True)
lock.close()
print('Evidence directory: '+folder.name)
