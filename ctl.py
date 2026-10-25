"""Operator CLI. Credentials remain in .env or the process environment, not command arguments."""
import argparse,json,os,urllib.request
from pathlib import Path
p=Path(__file__).resolve().parent/'.env'
if p.exists():
 for line in p.read_text().splitlines():
  line=line.strip()
  if line and not line.startswith('#') and '=' in line:
   k,v=line.split('=',1);os.environ.setdefault(k,v.strip().strip('\"').strip("'"))
a=argparse.ArgumentParser()
a.add_argument('action',choices=['health','scan','work','jobs','metrics','run','job','assign','receipt','download','deliver'])
a.add_argument('value',nargs='?')
a.add_argument('--base',default='http://127.0.0.1:8088')
args=a.parse_args();body=None
paths={'health':'/health','scan':'/run','work':'/run','jobs':'/jobs','metrics':'/metrics',
'run':'/runs/'+str(args.value),'job':'/jobs/'+str(args.value),'assign':'/tasks','receipt':'/receipts','download':'/jobs/'+str(args.value)+'/bundle','deliver':'/jobs/'+str(args.value)+'/deliver'}
if args.action=='deliver':body={}
if args.action in ('scan','work'):body={'discover':args.action=='scan'}
if args.action in ('assign','receipt'):body=json.loads(Path(args.value).read_text())
req=urllib.request.Request(args.base+paths[args.action],data=json.dumps(body).encode() if body is not None else None,
 headers={'Authorization':'Bearer '+os.environ.get('ENGINE_TOKEN',''),'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(req,timeout=30) as r:raw=r.read()
 if args.action=='download':
  target=Path('deliverable-'+args.value+'.zip');target.write_bytes(raw);print(target)
 else:print(json.dumps(json.loads(raw),indent=2))
except urllib.error.HTTPError as e:
 print('HTTP',e.code,e.read().decode());raise SystemExit(1)
