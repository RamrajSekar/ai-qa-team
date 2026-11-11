"""Developer-only profile-location comparison; no API configuration changes."""
import sys,json,uuid,tempfile,subprocess,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'visual-runner'))
if len(sys.argv)>1 and sys.argv[1]=='--child':
    workspace=Path(sys.argv[2]);config=json.loads((workspace/'config.json').read_text())
    from lab.webdriver import DirectWebDriver
    original=DirectWebDriver.call
    def call(self,method,path,payload=None):
        if method=='POST' and path=='/session' and config.get('diagnostic_profile'):
            profile=Path(config['diagnostic_profile'])
            profile.parent.mkdir(parents=True,exist_ok=True)
            args=payload['capabilities']['alwaysMatch']['goog:chromeOptions']['args']
            args[:]=[f'--user-data-dir={profile}' if arg.startswith('--user-data-dir=') else arg for arg in args]
            self.workspace=profile.parent  # Diagnostics read only this profile's port-file existence.
        return original(self,method,path,payload)
    DirectWebDriver.call=call
    from lab.supervisor import main
    sys.argv=[sys.argv[0],str(workspace)];main();raise SystemExit()
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--chrome',required=True);parser.add_argument('--driver',required=True);options=parser.parse_args()
sys.path.insert(0,str(ROOT/'visual-runner/tests'))
from startup_series import run_one
croot=Path(tempfile.mkdtemp(prefix='aiqa-profile-comparison-'))
if croot.drive.upper()!='C:':raise SystemExit('Expected private C temporary directory')
rows=[];active_label=None;original_popen=subprocess.Popen
profiles=[]
def popen(args,*pos,**kwargs):
    if isinstance(args,list) and len(args)>2 and args[1:3]==['-m','lab.supervisor']:
        workspace=Path(args[3]);profile=(croot/workspace.name/'profile') if active_label=='C' else workspace/'profile'
        config=json.loads((workspace/'config.json').read_text());config['diagnostic_profile']=str(profile)
        (workspace/'config.json').write_text(json.dumps(config));profiles.append(profile)
        args=[args[0],str(Path(__file__).resolve()),'--child',str(workspace)]
    return original_popen(args,*pos,**kwargs)
subprocess.Popen=popen
out=ROOT/'tmp'/('profile-location-'+uuid.uuid4().hex+'.json')
for label in ['F','C','C','F']:
    active_label=label
    try:row=run_one(ROOT/'visual-runner',sys.executable,options.chrome,options.driver,False)
    except Exception as exc:
        rows.append({'profile_volume':label,'error':type(exc).__name__,'cleanup':'unverified'});out.write_text(json.dumps(rows,indent=2));raise
    row['profile_volume']=label;rows.append(row);out.write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
    if row['cleanup']!='no_survivors_observed':raise SystemExit('Stopped: cleanup unverified')
    if label=='C':
        target=profiles[-1].resolve();target.relative_to(croot.resolve());shutil.rmtree(target,ignore_errors=True)
subprocess.Popen=original_popen
print('Evidence file: '+out.name,flush=True)
