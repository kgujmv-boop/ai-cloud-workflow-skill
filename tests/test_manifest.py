import io, math, subprocess, sys, tempfile, copy, importlib.util, pathlib, unittest
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/validate_manifest.py'
s=importlib.util.spec_from_file_location('validator',p);v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.x={'project_id':'example','tasks':[{'task_id':'a','revision':1,'input_sha256':'a'*64,'script_sha256':'b'*64,'parameters':{},'model_revision':None,'resource':'cpu','shard_id':'s1','dependencies':[],'status':'claimed','owner':'worker-a','lease_until':'2099-01-01T00:00:00Z'}]}
    def test_valid(self): self.assertEqual(v.validate(self.x),[])
    def test_duplicate_equivalent_job(self):
        self.x['tasks'].append(dict(self.x['tasks'][0],task_id='b',owner='worker-b')); self.assertTrue(any('equivalent' in x for x in v.validate(self.x)))
    def test_expired_is_not_reclaimable(self):
        self.x['tasks'][0]['lease_until']='2000-01-01T00:00:00Z'; self.assertTrue(any('expired' in x for x in v.validate(self.x)))
    def test_cycle(self):
        self.x['tasks'][0]['dependencies']=['a']; self.assertTrue(any('cycle' in x for x in v.validate(self.x)))
    def test_done_requires_output(self):
        self.x['tasks'][0]['status']='done'; self.assertTrue(any('outputs' in x for x in v.validate(self.x)))
    def test_submitted_requires_receipt(self):
        self.x['tasks'][0]['status']='submitted'; self.assertTrue(any('submission_ref' in x for x in v.validate(self.x)))
    def test_malformed_id(self):
        self.x['tasks'][0]['task_id']=[];self.assertTrue(v.validate(self.x))
    def test_bad_output_types(self):
        for bad in (42,{},'yes'):
            x=copy.deepcopy(self.x);x['tasks'][0].update(status='done',outputs=bad);self.assertTrue(v.validate(x))
    def test_verified_requires_boolean(self):
        self.x['tasks'][0].update(status='done',outputs=[{'sha256':'c'*64,'verified':'yes'}]);self.assertTrue(v.validate(self.x))
    def test_wrong_hash(self):
        self.x['tasks'][0]['input_sha256']='wrong';self.assertTrue(v.validate(self.x))
    def completed(self,task=None):
        t=copy.deepcopy(task or self.x['tasks'][0]);t.update(status='done',outputs=[{'location':'outputs/a.json','sha256':'c'*64,'verified':True}]);return t
    def test_valid_done(self):
        self.x['tasks']=[self.completed()];self.assertEqual(v.validate(self.x),[])
    def test_done_location_required(self):
        for location in (None,'', '  ', 123, [], {}):
            t=self.completed();t['outputs'][0]['location']=location
            self.assertTrue(v.validate(dict(self.x,tasks=[t])))
    def test_done_uri_allowed(self):
        t=self.completed();t['outputs'][0]['location']='https://example.org/private/output.json'
        self.assertEqual(v.validate(dict(self.x,tasks=[t])),[])
    def test_done_dependencies_must_be_done(self):
        t=self.completed();t['dependencies']=['b'];b=dict(self.x['tasks'][0],task_id='b',status='blocked')
        self.assertTrue(any('not done' in e for e in v.validate(dict(self.x,tasks=[t,b]))))
    def test_completed_equivalent_blocks_in_both_orders(self):
        t=self.completed();active=dict(self.x['tasks'][0],task_id='b')
        for tasks in ([t,active],[active,t]):self.assertTrue(any('completed work' in e for e in v.validate(dict(self.x,tasks=tasks))))
    def test_explicit_recompute_allowed(self):
        t=self.completed();active=dict(self.x['tasks'][0],task_id='b',recompute_reason='Repeat sample to check nondeterminism')
        self.assertEqual(v.validate(dict(self.x,tasks=[t,active])),[])
    def test_reason_does_not_override_active_duplicate(self):
        self.x['tasks'].append(dict(self.x['tasks'][0],task_id='b',recompute_reason='Repeat'))
        self.assertTrue(any('equivalent active' in e for e in v.validate(self.x)))
    def test_reason_types(self):
        for value in ('','  ',False,12,[],{}):
            x=copy.deepcopy(self.x);x['tasks'][0]['recompute_reason']=value;self.assertTrue(v.validate(x))
    def test_identity_components_change_work(self):
        t=self.completed()
        for k,value in [('input_sha256','d'*64),('script_sha256','e'*64),('parameters',{'a':2}),('model_revision','v2'),('shard_id','s2')]:
            active=dict(self.x['tasks'][0],task_id='b');active[k]=value
            self.assertEqual(v.validate(dict(self.x,tasks=[t,active])),[],k)
    def test_revision_and_resource_do_not_change_equivalence(self):
        t=self.completed();active=dict(self.x['tasks'][0],task_id='b',revision=2,resource='another-cpu')
        self.assertTrue(any('completed work' in e for e in v.validate(dict(self.x,tasks=[t,active]))))
    def test_owner_type(self):
        self.x['tasks'][0]['owner']=['worker'];self.assertTrue(v.validate(self.x))
    def test_receipt_type(self):
        self.x['tasks'][0].update(status='submitted',submission_ref=42);self.assertTrue(v.validate(self.x))
    def test_deep_acyclic_graph(self):
        tasks=[dict(self.x['tasks'][0],task_id=str(i),status='planned',dependencies=[str(i+1)] if i<1499 else []) for i in range(1500)]
        self.assertEqual(v.validate(dict(self.x,tasks=tasks)),[])
    def test_deep_cycle(self):
        tasks=[dict(self.x['tasks'][0],task_id=str(i),status='planned',dependencies=[str((i+1)%1100)]) for i in range(1100)]
        self.assertTrue(any('cycle' in e for e in v.validate(dict(self.x,tasks=tasks))))
    def test_strict_json_reader(self):
        for raw in ('{"tasks":[],"tasks":[]}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(ValueError):v.load_manifest(io.StringIO(raw))
    def test_nonfinite_parameters(self):
        self.x['tasks'][0]['parameters']={'x':math.nan};self.assertTrue(v.validate(self.x))
    def test_blank_identity_strings(self):
        for k in ('project_id','task_id','shard_id','resource'):
            x=copy.deepcopy(self.x)
            if k=='project_id':x[k]='  '
            else:x['tasks'][0][k]='  '
            self.assertTrue(v.validate(x),k)
    def test_cli_diagnostics_stay_json(self):
        import json
        malformed=['['*10000+'0'+']'*10000, '{"project_id":"x","tasks":[{"task_id":"\\ud800"}]}']
        for raw in malformed:
            with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
                f.write(raw);f.flush();result=subprocess.run([sys.executable,str(p),f.name],capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertNotIn('Traceback',result.stderr)
if __name__=='__main__': unittest.main()
