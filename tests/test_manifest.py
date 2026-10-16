import copy, importlib.util, pathlib, unittest
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
if __name__=='__main__': unittest.main()
