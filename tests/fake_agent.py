"""Protocol fixture, never a model and never a desktop driver."""
import json
import sys
import threading
import time

write_lock = threading.Lock()
generation = 0
def send(value):
    with write_lock:
        sys.stdout.buffer.write((json.dumps(value, ensure_ascii=False) + "\n").encode())
        sys.stdout.buffer.flush()

def run(message, captured_generation):
    send({"type": "agent_start"})
    send({"type": "message_start", "message": {"role": "assistant"}})
    send({"type": "message_update", "assistantMessageEvent": {"type": "thinking_delta", "delta": "PRIVATE THINKING"}})
    send({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "Respuesta\u2028" + message}})
    if message == "wait":
        time.sleep(.4)
    if captured_generation != generation:
        return
    send({"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "Respuesta\u2028" + message}]}})
    send({"type": "agent_end", "messages": [], "willRetry": False})
    time.sleep(.08)
    send({"type": "agent_settled"})

for line in sys.stdin.buffer:
    record = json.loads(line)
    if record.get("jsonrpc"):
        method = record["method"]
        if "id" not in record:
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo fixture", "inputSchema": {"type": "object"}}]}
        else:
            result = {"content": [{"type": "text", "text": json.dumps(record["params"]["arguments"], ensure_ascii=False)}]}
        send({"jsonrpc": "2.0", "id": record["id"], "result": result})
        continue
    kind = record["type"]
    data = {"model": {"id": "fixture", "provider": "test"}, "isStreaming": False} if kind == "get_state" else {}
    if kind == "prompt":
        data = {"disposition": "started"}
    if kind == "abort":
        generation += 1
    send({"type": "response", "id": record.get("id"), "command": kind, "success": True, "data": data})
    if kind == "prompt":
        threading.Thread(target=run, args=(record["message"], generation), daemon=True).start()
