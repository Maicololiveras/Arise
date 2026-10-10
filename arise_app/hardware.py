"""Conservative CPU profiles; no CUDA requirement or automatic cloud fallback."""
import os

def local_profile(config,total_bytes=None):
    choice=config.get('local_profile','auto')
    if choice in ('light','standard'):return choice
    if total_bytes is None:
        import psutil
        total_bytes=psutil.virtual_memory().total
    return 'light' if total_bytes<=10*1024**3 else 'standard'

def server_command(config):
    command=list(config.get('local_server_command',[]))
    if local_profile(config)!='light' or not command:return command
    # Only adjust ARISE's owned llama.cpp server; preserve custom commands.
    from pathlib import Path
    if Path(command[0]).stem!='llama-server':return command
    for flag,value in (('--ctx-size','4096'),('--threads',str(max(1,min(4,os.cpu_count() or 2))))):
        if flag in command:
            index=command.index(flag)
            if index+1<len(command):command[index+1]=value
        else:command.extend([flag,value])
    return command
