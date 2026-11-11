"""Read-only final process/log observation for an already stopped task-owned fixture."""
import argparse
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
args = parser.parse_args()
report = json.loads((args.directory/'report.json').read_text())
ids = [str(value) for row in report['checks'] for key,value in row.items() if key in ('run_id','interrupted_run','later_run')]
text = (args.directory/'api-private.log').read_text(errors='replace')
ids = sorted(set(ids) | set(re.findall(r'/visual-lab/runs/([0-9a-f]{32})', text)))
if not ids or not all(re.fullmatch('[0-9a-f]{32}',value) for value in ids): raise SystemExit('Invalid/missing fixture IDs')
pattern = '|'.join(ids)
command = f"@(Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -ne $PID -and $_.CommandLine -match '{pattern}' }}).Count"
probe = subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=15)
count = int(probe.stdout.strip()) if probe.returncode==0 and probe.stdout.strip().isdigit() else 'UNVERIFIED'
result = {'remaining_fixture_profile_processes':count,
          'fixture_run_ids_observed':len(ids),
          'jwt_shaped_values_in_private_API_log':re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',text) is not None,
          'cookie_dump_marker_in_private_API_log':'Cookies received' in text}
(args.directory/'cleanup-observation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
