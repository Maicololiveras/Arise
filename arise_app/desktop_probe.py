"""Read-only Gentle Desktop RPC discovery, scoped to one Pi process."""
import json
from uuid import uuid4

SCHEMA="gentle-shell.desktop-rpc/v1"

class DesktopProbe:
    def __init__(self, process):
        self.process=process
        self.pending={}
        self.state={"status":"loading"}

    def request(self, method):
        key=uuid4().hex
        self.pending[key]=method
        message=json.dumps(dict(schema=SCHEMA,requestId=key,method=method,params={}))
        try:self.process.send({"type":"prompt","id":uuid4().hex,"message":"/gentle:desktop "+message})
        except (RuntimeError,OSError):
            self.pending.pop(key,None);self.state["status"]="unavailable"

    def widget(self,event):
        lines=event.get("widgetLines")
        if not isinstance(lines,list) or len(lines)!=1 or not isinstance(lines[0],str) or len(lines[0])>65536:return
        try:r=json.loads(lines[0])
        except ValueError:return
        if not isinstance(r,dict) or r.get("schema")!=SCHEMA or r.get("kind")!="response":return
        key=r.get("requestId")
        if not isinstance(key,str):return
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
            if "get_snapshot" in methods:self.request("get_snapshot")
        elif method=="get_snapshot" and type(data.get("sequence")) is int:
            self.state["sequence"]=data["sequence"]
