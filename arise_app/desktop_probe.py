"""Read-only Gentle Desktop RPC discovery, scoped to one Pi process."""
import json
import queue
import threading
from uuid import uuid4

SCHEMA="gentle-shell.desktop-rpc/v1"

class DesktopProbe:
    def __init__(self, process):
        self.process=process
        self.pending={}
        self.waiters = {}
        self.waiter_lock = threading.Lock()
        self.state={"status":"loading"}

    def request(self, method):
        key=uuid4().hex
        self.pending[key]=method
        message=json.dumps(dict(schema=SCHEMA,requestId=key,method=method,params={"store":"profiles"} if method=="get_config" else {}))
        try:self.process.send({"type":"prompt","id":uuid4().hex,"message":"/gentle:desktop "+message})
        except (RuntimeError,OSError):
            self.pending.pop(key,None);self.state["status"]="unavailable"

    def call(self, method, params):
        key = uuid4().hex
        waiting = queue.Queue(maxsize=1)
        with self.waiter_lock:
            self.waiters[key] = waiting
        try:
            message = json.dumps(dict(schema=SCHEMA, requestId=key, method=method, params=params))
            self.process.send({"type": "prompt", "id": uuid4().hex, "message": "/gentle:desktop " + message})
            try:
                reply = waiting.get(timeout=12)
            except queue.Empty:
                raise RuntimeError("Gentle no confirmó la operación. Actualiza el estado antes de repetirla.") from None
            if reply.get("ok") is not True:
                raise RuntimeError(reply.get("error", {}).get("message", "Gentle rechazó la operación."))
            return reply.get("data", {})
        finally:
            with self.waiter_lock:
                self.waiters.pop(key, None)

    def refresh(self):
        for method in ("get_snapshot","get_permission_mode","get_config","list_jobs"):
            if method in self.state.get("methods",[]) and method not in self.pending.values():
                self.request(method)

    def widget(self,event):
        lines=event.get("widgetLines")
        if not isinstance(lines,list) or len(lines)!=1 or not isinstance(lines[0],str) or len(lines[0])>2_000_000:return
        try:r=json.loads(lines[0])
        except ValueError:return
        if not isinstance(r,dict) or r.get("schema")!=SCHEMA:return
        if r.get("kind")=="event":
            seq=r.get("seq")
            if type(seq)!=int or seq<0:return
            previous=self.state.get("sequence",-1)
            if seq<=previous:return
            gap=previous>=0 and seq!=previous+1
            self.state["sequence"]=seq
            if gap or r.get("event") in ("permission_mode_changed","config_changed","jobs_update"):
                for field in ("permission","profile","jobs"):self.state.pop(field,None)
                self.refresh()
            return
        if r.get("kind")!="response":return
        key=r.get("requestId")
        if not isinstance(key,str):return
        with self.waiter_lock:
            waiting = self.waiters.pop(key, None)
        if waiting is not None:
            waiting.put_nowait(r)
            return
        method=self.pending.pop(key,None)
        if not method:return
        data=r.get("data")
        if r.get("ok") is not True or not isinstance(data,dict):
            self.state["status"]="unavailable";return
        if method=="capabilities":
            methods=data.get("methods",[])
            if not isinstance(methods,list) or not all(isinstance(m,str) for m in methods):
                self.state["status"]="unavailable";return
            self.state.update(status="ready",methods=methods)
            self.refresh()
        elif method=="get_snapshot" and type(data.get("sequence")) is int:
            self.state["sequence"]=max(self.state.get("sequence",-1),data["sequence"])
        elif method=="get_permission_mode" and data.get("mode") in ("normal","auto","yolo","super-yolo"):
            self.state["permission"]=data["mode"]
        elif method=="get_config" and data.get("store")=="profiles" and data.get("status")=="ok":
            value=data.get("value")
            if isinstance(value,dict) and isinstance(value.get("active"),str):
                self.state["profile"]=value["active"][:100]
        elif method=="list_jobs" and isinstance(data.get("jobs"),list):
            self.state["jobs"]=len(data["jobs"])
