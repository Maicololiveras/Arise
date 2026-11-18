"""One persistent loopback connection for one desktop renderer's event cursor."""
import http.client
import json
from urllib.parse import urlsplit


def receive(remote, cursor, stopped, deliver, disconnected):
    """Deliver in order. Advance only once the renderer acknowledges the batch."""
    url=urlsplit(remote.url)
    if url.scheme!="http" or url.hostname!="127.0.0.1" or not url.port:
        raise ValueError("Invalid resident address")
    headers={"Authorization":"Bearer "+remote.token,"X-Arise-Accounts":remote.accounts_token}
    while not stopped.is_set():
        conn=http.client.HTTPConnection(url.hostname,url.port,timeout=5)
        try:
            while not stopped.is_set():
                conn.request("GET","/api/desktop/events?after="+str(cursor),headers=headers)
                reply=conn.getresponse()
                if reply.status!=200:raise OSError("Desktop feed unavailable")
                batch=json.loads(reply.read())
                if stopped.is_set():return
                if batch["events"] or batch["gap"]:
                    if not deliver(batch):return
                cursor=batch["cursor"]
        except (OSError,http.client.HTTPException,ValueError,KeyError):
            if not stopped.is_set():disconnected()
            stopped.wait(1)
        finally:conn.close()
