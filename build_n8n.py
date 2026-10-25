import json,uuid
from pathlib import Path
nodes=[]
def add(name,typ,params,x,y=0,v=1):
 n={'id':str(uuid.uuid4()),'name':name,'type':'n8n-nodes-base.'+typ,'typeVersion':v,'position':[x,y],'parameters':params};nodes.append(n);return n
add('Manual test','manualTrigger',{},0)
add('8 AM and 8 PM Mexico City','scheduleTrigger',{'rule':{'interval':[{'field':'cronExpression','expression':'0 8,20 * * *'}]}},0,180,1.2)
add('Engine settings','code',{'jsCode':"return [{json:{engineUrl:'http://paid-task-engine:8080', startedAt:Date.now()}}];"},220,v=2)
auth={'authentication':'genericCredentialType','genericAuthType':'httpHeaderAuth'}
add('Start run','httpRequest',{'method':'POST','url':"={{ $('Engine settings').first().json.engineUrl + '/run' }}",**auth,'sendBody':True,'specifyBody':'json','jsonBody':'{"discover":true}','options':{'timeout':30000}},440,v=4.2)
add('Wait 30 seconds','wait',{'amount':30,'unit':'seconds'},660,v=1.1)
add('Check run','httpRequest',{'url':"={{ $('Engine settings').first().json.engineUrl + '/runs/' + $json.run_id }}",**auth,'options':{'timeout':30000}},880,v=4.2)
add('Still running','if',{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':str(uuid.uuid4()),'leftValue':"={{ $json.status === 'running' && Date.now() - $('Engine settings').first().json.startedAt < 900000 }}",'rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}},1100,v=2.2)
add('Telegram digest','code',{'jsCode':"const r=$input.first().json; return [{json:{text:(r.status==='running' ? 'Engine still running after 15 minutes. Inspect run '+r.run_id+'; do not start duplicate work.' : r.report || 'Run ended with status '+r.status).slice(0,3800)}}];"},1320,100,v=2)
add('Send to Telegram','telegram',{'resource':'message','operation':'sendMessage','chatId':'REPLACE_WITH_YOUR_CHAT_ID','text':'={{ $json.text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;") }}','additionalFields':{'parse_mode':'HTML','disable_web_page_preview':True,'appendAttribution':False}},1540,100,v=1.2)
add('SETUP','stickyNote',{'content':'## Paid Task Engine v2\nDeploy the included Python/Docker service first. This is an orchestrator, not a standalone worker.\n\n1. Create Header Auth credential: Name Authorization; Value Bearer YOUR_ENGINE_TOKEN. Select it in Start run and Check run.\n2. In Engine settings set the service URL. Docker n8n must share paid-task-net; host n8n can use http://127.0.0.1:8088.\n3. Select Telegram credential and replace Chat ID.\n4. Test manually, then publish.\n\nDiscovery: public indexed requests, no marketplace dependence.\nFulfillment: confirmed research/dataset tasks submitted to /tasks.\nAuto delivery: off until you configure a buyer profile and enable it.\nNo automated negotiation, social posting, wallet access or guaranteed income.\n\nRead README.md for scope, cost allowance caveats, intake, and delivery.','height':520,'width':480},180,-580)
connections={}
def edge(a,b,index=0):
 connections.setdefault(a,{'main':[]})
 while len(connections[a]['main'])<=index:connections[a]['main'].append([])
 connections[a]['main'][index].append({'node':b,'type':'main','index':0})
for a,b in [('Manual test','Engine settings'),('8 AM and 8 PM Mexico City','Engine settings'),('Engine settings','Start run'),('Start run','Wait 30 seconds'),('Wait 30 seconds','Check run'),('Check run','Still running'),('Still running','Wait 30 seconds'),('Telegram digest','Send to Telegram')]:edge(a,b)
edge('Still running','Telegram digest',1)
w={'name':'Paid Task Engine v2 - Control and Telegram','nodes':nodes,'connections':connections,'active':False,'settings':{'executionOrder':'v1','timezone':'America/Mexico_City','executionTimeout':1200},'pinData':{},'tags':[]}
Path(__file__).with_name('paid-task-engine-n8n.json').write_text(json.dumps(w,indent=2))
