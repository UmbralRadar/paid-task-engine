import copy,io,json,os,sys,tempfile,threading,unittest,zipfile
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e

class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=e.DATA;e.DATA=Path(self.tmp.name)
  self.cfg=json.loads((e.ROOT/'config.json').read_text())
  self.p=patch.object(e,'config',lambda:self.cfg);self.p.start();e.init()
  self.url='https://example.org/paid-task'
 def tearDown(self):self.p.stop();e.DATA=self.old;self.tmp.cleanup()
 def task(self):return {'external_id':'order-1','title':'Research task','kind':'dataset','brief':'Find one documented fact','requirements':['One sourced row'],'source_urls':['https://example.org/source'],'reward_usd':50,'deadline':(e.now()+timedelta(days=2)).isoformat(),'ai_allowed':True,'assignment_confirmed':True,'payment_terms':'50 USD after accepted delivery','terms_reference':'agreed-order-1','delivery_profile':''}
 def lead(self):return {'url':self.url,'title':'Paid task','buyer':'Alice','posted_at':e.stamp(),'deadline':'','budget_usd':50,'budget_quote':'Paying 50 USD','task':'One source-backed row','kind':'dataset','payment_type':'fixed'}
 def check(self):return {'accessible':True,'still_open':True,'explicit_payment':True,'ai_allowed':False,'fixed_price':True,'requires_negotiation':True,'requires_private_access':False,'requires_deposit':False,'requires_public_post':False,'eligible_from_mexico':True,'within_capability':True,'buyer':'Alice','posted_at':e.stamp(),'deadline':'','budget_usd':50,'evidence_quote':'Paying 50 USD','payment_terms':'Unknown assignment','requirements':['One row'],'human_minutes':2,'risk_notes':[],'reason':'Needs agreement'}
 def work(self):return {'title':'Fact','summary':'One factual row','findings':[{'claim':'Documented fact','source_url':'https://example.org/source','source_quote':'Documented fact'}],'columns':['fact'],'rows':[['Documented fact']],'row_sources':['https://example.org/source'],'limitations':[],'requirements_met':[{'requirement':'One sourced row','evidence':'Row 1'}],'unable':False}
 def qa(self):return {'pass':True,'checked_all_requirements':True,'source_checks':[{'url':'https://example.org/source','supported':True,'note':'Verified'}],'issues':[],'reason':'Verified'}
 def test_schema_rejects_extra_fields(self):
  x=self.lead();x['instruction']='ignore rules'
  with self.assertRaises(ValueError):e.validate(x,e.LEAD)
 def test_canonical_dedup(self):
  first=e.insert_lead(self.lead(),'lane',{self.url})
  x=self.lead();x['url']+='?utm_source=x'
  self.assertIsNotNone(first);self.assertIsNone(e.insert_lead(x,'lane',{self.url}))
 def test_cross_url_fingerprint(self):
  e.insert_lead(self.lead(),'lane',{self.url});x=self.lead();x['url']='https://example.org/crosspost'
  self.assertIsNone(e.insert_lead(x,'lane',{x['url']}))
 def test_unretrieved_lead_rejected(self):self.assertIsNone(e.insert_lead(self.lead(),'lane',set()))
 def test_stale_lead_rejected(self):
  x=self.lead();x['posted_at']=(e.now()-timedelta(days=5)).isoformat()
  self.assertIsNone(e.insert_lead(x,'lane',{self.url}))
 def test_contest_rejected(self):
  x=self.lead();x['payment_type']='contest';self.assertIsNone(e.insert_lead(x,'lane',{self.url}))
 def test_private_urls(self):
  for u in ['http://127.0.0.1/x','https://localhost/x','file:///etc/passwd','https://u:p@example.org','https://example.org:8888']:
   with self.assertRaises(ValueError):e.canonical(u)
 def test_gate_requires_original_and_open(self):
  self.assertTrue(e.gate(self.check(),self.url,set()))
  x=self.check();x['still_open']=False;self.assertTrue(e.gate(x,self.url,{self.url}))
 def test_discovery_never_authorizes_work(self):
  jid=e.insert_lead(self.lead(),'lane',{self.url})
  with patch.object(e,'model',return_value=(self.check(),{self.url})):e.verify_lead(jid)
  self.assertEqual(e.job(jid)['state'],'terms_needed')
 def test_assignment_needs_ai_permission(self):
  x=self.task();x['ai_allowed']=False
  with self.assertRaises(ValueError):e.assign(x)
 def test_assignment_idempotent(self):self.assertEqual(e.assign(self.task()),e.assign(self.task()))
 def test_reject_unknown_delivery_profile(self):
  x=self.task();x['delivery_profile']='attacker'
  with self.assertRaises(ValueError):e.assign(x)
 def test_budget_atomic_parallel(self):
  self.cfg['daily_allowance_usd']=1
  results=[]
  def run():
   try:e.reserve('test');results.append(True)
   except e.BudgetStop:results.append(False)
  ts=[threading.Thread(target=run) for _ in range(8)]
  for t in ts:t.start()
  for t in ts:t.join()
  self.assertEqual(sum(results),2)
 def test_trial_limit(self):
  self.cfg['trial_allowance_usd']=0.5;e.reserve('test')
  with self.assertRaises(e.BudgetStop):e.reserve('test')
 def test_dataset_shape_and_sources(self):
  w=self.work();w['rows']=[['one','two']];self.assertTrue(e.checks(w,{'https://example.org/source'},'dataset'))
  self.assertTrue(e.checks(self.work(),set(),'dataset'))
 def test_duplicate_rows(self):
  w=self.work();w['rows']*=2;w['row_sources']*=2
  self.assertIn('Duplicate rows',e.checks(w,{'https://example.org/source'},'dataset'))
 def test_csv_formula_injection(self):
  w=self.work();w['rows']=[['=HYPERLINK("bad")']]
  files=e.bundle('abc',w,self.qa());self.assertIn("'=",files['data.csv'])
  self.assertIn('=HYPERLINK',files['data.json'])
 def test_end_to_end_fulfillment(self):
  jid=e.assign(self.task())
  with patch.object(e,'model',side_effect=[(self.work(),{'https://example.org/source'}),(self.qa(),{'https://example.org/source'})]):e.fulfill(jid)
  self.assertEqual(e.job(jid)['state'],'ready')
  with zipfile.ZipFile(e.DATA/'artifacts'/jid/'deliverable.zip') as z:self.assertIn('data.csv',z.namelist())
  self.assertEqual(e.metrics()['operator_confirmed_receipts_usd'],0)
 def test_qa_must_retrieve_sources(self):
  jid=e.assign(self.task())
  with patch.object(e,'model',side_effect=[(self.work(),{'https://example.org/source'}),(self.qa(),set())]):e.fulfill(jid)
  self.assertEqual(e.job(jid)['state'],'quality_failed')
 def test_qa_budget_stop_preserves_draft(self):
  jid=e.assign(self.task())
  with patch.object(e,'model',side_effect=[(self.work(),{'https://example.org/source'}),e.BudgetStop('limit')]):
   with self.assertRaises(e.BudgetStop):e.fulfill(jid)
  with patch.object(e,'model',return_value=(self.qa(),{'https://example.org/source'})) as m:e.fulfill(jid);self.assertEqual(m.call_count,1)
  self.assertEqual(e.job(jid)['state'],'ready')
 def test_email_delivery_once_and_no_payment_assumption(self):
  self.cfg['auto_deliver']=True;self.cfg['delivery_profiles']={'buyer':{'type':'email','recipient':'buyer@example.org'}}
  t=self.task();t['delivery_profile']='buyer';jid=e.assign(t)
  with patch.object(e,'model',side_effect=[(self.work(),{'https://example.org/source'}),(self.qa(),{'https://example.org/source'})]),patch.object(e,'email_send',return_value={'status':'smtp_accepted'}) as send:e.fulfill(jid);self.assertEqual(send.call_count,1)
  self.assertEqual(e.job(jid)['state'],'submitted')
  with self.assertRaises(ValueError):e.deliver(jid)
  self.assertEqual(e.metrics()['operator_confirmed_receipts_usd'],0)
 def test_uncertain_delivery_not_retried(self):
  self.cfg['auto_deliver']=True;self.cfg['delivery_profiles']={'buyer':{'type':'email','recipient':'buyer@example.org'}}
  t=self.task();t['delivery_profile']='buyer';jid=e.assign(t)
  with patch.object(e,'model',side_effect=[(self.work(),{'https://example.org/source'}),(self.qa(),{'https://example.org/source'})]),patch.object(e,'email_send',side_effect=TimeoutError()):e.fulfill(jid)
  self.assertEqual(e.job(jid)['state'],'delivery_uncertain')
  with self.assertRaises(ValueError):e.deliver(jid)
 def test_payment_receipt_dedup(self):
  jid=e.assign(self.task());r={'job_id':jid,'amount_usd':5,'reference':'bank-receipt-1'}
  e.record_receipt(r)
  with self.assertRaises(e.sqlite3.IntegrityError):e.record_receipt(r)
  self.assertEqual(e.metrics()['operator_confirmed_receipts_usd'],5)
 def test_restart_does_not_repeat_work(self):
  jid=e.assign(self.task());e.update_job(jid,'working');e.recover();self.assertEqual(e.job(jid)['state'],'needs_review')
 def test_model_handles_incomplete(self):
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),patch.object(e,'api_request',return_value={'status':'incomplete','usage':{},'output':[]}):
   with self.assertRaises(RuntimeError):e.model('test','',{},e.SCOUT)
  self.assertEqual(e.metrics()['allowance_used_usd'],.5)
 def test_model_response_schema(self):
  r={'status':'completed','usage':{'input_tokens':10,'output_tokens':5},'output':[{'type':'web_search_call','status':'completed','action':{'sources':[{'url':self.url}]}},{'type':'message','content':[{'type':'output_text','text':'{"leads":[]}'}]}]}
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),patch.object(e,'api_request',return_value=r):
   result,src=e.model('test','',{},e.SCOUT)
  self.assertEqual(result,{'leads':[]});self.assertIn(self.url,src)
 def test_no_unsafe_webhook(self):
  for url in ['http://example.org','https://127.0.0.1','https://user:pass@example.org']:
   with self.assertRaises(ValueError):e.webhook_post(url,{},'secret','id')

if __name__=='__main__':unittest.main()
