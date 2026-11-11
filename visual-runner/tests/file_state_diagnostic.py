import sys,time,json,uuid,shutil,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'visual-runner'))
from lab.runtime import BrowserLock,WindowsProcessTree,runner_environment
work=root/'tmp'/('cold-file-study-'+uuid.uuid4().hex);work.mkdir()
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--cached',required=True);parser.add_argument('--fresh',required=True)
parser.add_argument('--copy-root', type=Path)
parser.add_argument('--pair-only', action='store_true')
options=parser.parse_args()
cached=Path(options.cached);fresh=Path(options.fresh)
copy=(options.copy_root / ('aiqa-cft-copy-'+uuid.uuid4().hex) if options.copy_root else work/'copied-cached');shutil.copytree(cached,copy)
p=subprocess.run([str(copy/'setup.exe'),f'--configure-browser-in-directory={copy}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
if p.returncode not in (0,78):raise SystemExit('Sandbox directory configuration failed')
bundles={'fresh':fresh,'cached':cached,'copied_cached':copy};report={'read_times':[],'attempts':[]}
for label in (['copied_cached','cached'] if options.pair_only else ['copied_cached','fresh','cached']):
 t=time.monotonic();digest=hashlib.sha256((bundles[label]/'chrome.dll').read_bytes()).hexdigest();report['read_times'].append({'bundle':label,'seconds':round(time.monotonic()-t,3),'sha256':digest})
lock=BrowserLock(root/'visual-runner/.runtime/browser.lock')
try:
 for label in (['cached','copied_cached','copied_cached','cached'] if options.pair_only else ['fresh','cached','copied_cached','copied_cached','cached','fresh']):
  path=work/uuid.uuid4().hex;path.mkdir();tree=WindowsProcessTree();start=time.monotonic();proc=None
  row={'bundle':label,'order':len(report['attempts'])+1,'result':'launch_not_completed'}
  try:
   proc=tree.launch([str(bundles[label]/'chrome.exe'),'--headless=new','--remote-debugging-port=0',f'--user-data-dir={path / "profile"}','--no-first-run','--no-default-browser-check','--disable-background-networking','--enable-logging',f'--log-file={path / "chrome.log"}','about:blank'],env=runner_environment(),cwd=root/'visual-runner')
   deadline=start+45
   while proc.poll() is None and time.monotonic()<deadline and not (path/'profile/DevToolsActivePort').exists():time.sleep(.1)
   row={'bundle':label,'order':len(report['attempts'])+1,'elapsed':round(time.monotonic()-start,3),'endpoint_file':(path/'profile/DevToolsActivePort').exists(),'exit_before_cleanup':proc.poll(),'browser_before_cleanup':tree.browser_status()}
  finally:
   tree.close()
   if proc:proc.wait(timeout=5)
   deadline=time.monotonic()+3
   while tree.browser_status()=='running' and time.monotonic()<deadline:time.sleep(.1)
   row['browser_after_cleanup']=tree.browser_status();tree.release_observations()
  report['attempts'].append(row);(work/'sanitized.json').write_text(json.dumps(report,indent=2));print(json.dumps(row),flush=True)
  if row['browser_after_cleanup']=='running':raise SystemExit('Cleanup unverified; stopped')
finally:lock.close()
print('Evidence directory: '+work.name,flush=True)
