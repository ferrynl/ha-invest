import sys
sys.path.insert(0,'/app')
import http.client,json,os,secrets,signal,threading,time
from uuid import uuid4
from feedback_service.store import RelayStore
import feedback_service.__main__ as entry
os.umask(0o077)
os.environ['SERVICE_SECRET']='s'*40
os.environ['GITHUB_WEBHOOK_SECRET']='w'*40
os.environ['FEEDBACK_DATABASE']='/data/smoke.sqlite3'
os.environ['PORT']='8080'
assert os.getuid()==10001
store=RelayStore('/data/smoke.sqlite3','s'*40)
code=store.invite();credential=secrets.token_urlsafe(32)
class FakeGitHub:
    repository_id=99
    count=0
    def board(self,etag=None):return {'issues':[],'limited':False,'checked_at':None},None
    def create(self,job):self.count+=1;return {'number':42}
fake=FakeGitHub();entry.github_client=lambda:fake
errors=[]
def request(path,data=None,authorized=False):
    conn=http.client.HTTPConnection('127.0.0.1',8080,timeout=2)
    try:
        headers={'Content-Type':'application/json'}
        if authorized:headers['Authorization']='Bearer '+credential
        conn.request('POST' if data else 'GET',path,json.dumps(data) if data else None,headers)
        response=conn.getresponse();return response.status,json.loads(response.read())
    finally:conn.close()
def checks():
    try:
        for _ in range(30):
            try:
                if request('/health')[0]==200:break
            except OSError:time.sleep(.1)
        assert request('/v1/issues')[0]==401
        assert request('/v1/enroll',{'code':code,'credential':credential})[0]==201
        data={'request_id':str(uuid4()),'kind':'wish','title':'Container smoke test','description':'Fake GitHub; no external network.','version':'0.39.0'}
        one=request('/v1/submissions',data,True);two=request('/v1/submissions',data,True)
        assert one[0]==two[0]==202 and one[1]['id']==two[1]['id']
        for _ in range(50):
            result=request('/v1/submissions',authorized=True)
            if result[1]['submissions'][0]['state']=='open':break
            time.sleep(.1)
        assert result[1]['submissions'][0]['number']==42
        assert fake.count==1
        identity=store.authenticate(credential);store.revoke(identity)
        assert request('/v1/submissions',authorized=True)[0]==401
        print('Container smoke passed: non-root, writable data, startup, health, activation, idempotent submission, worker, revocation and graceful shutdown.',flush=True)
    except Exception as error:errors.append(error)
    finally:os.kill(os.getpid(),signal.SIGTERM)
threading.Thread(target=checks,daemon=True).start()
import sys
sys.argv=['feedback_service','serve']
entry.main()
if errors:raise errors[0]
