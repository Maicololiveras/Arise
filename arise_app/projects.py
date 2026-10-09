"""One durable workspace and shell session per chat; only the selected chat runs."""
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
PREFERENCES = ("agent_provider", "agent_model", "thinking", "pi_command", "pi_extra_args", "gentle_path", "mcp", "code_enabled")

class ProjectSessions:
    def __init__(self, storage):
        self.storage=storage
        self.root=Path(os.environ.get('ARISE_CHAT_ROOT',str(storage.root/'chat'))).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        storage.db.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT,path TEXT UNIQUE,created REAL);
        CREATE TABLE IF NOT EXISTS chat_sessions(conversation TEXT PRIMARY KEY,project TEXT,ordinal INTEGER,folder TEXT,workspace TEXT,kind TEXT,branch TEXT);
        CREATE INDEX IF NOT EXISTS chat_project ON chat_sessions(project);
        ''')
        for conversation in storage.conversations():
            if not self.get(conversation['id']):
                project=self.project(storage.config['workspace'])
                self.attach(conversation['id'],project,isolated=False)

    def projects(self):
        with self.storage.lock:return [dict(r) for r in self.storage.db.execute('SELECT * FROM projects ORDER BY created')]

    def project(self,path,name=None):
        path=Path(path).resolve()
        if not path.is_dir():raise ValueError('La carpeta del proyecto debe existir')
        with self.storage.lock,self.storage.db:
            row=self.storage.db.execute('SELECT * FROM projects WHERE path=?',(str(path),)).fetchone()
            if row:return dict(row)
            project={'id':uuid.uuid4().hex,'name':name or path.name,'path':str(path),'created':time.time()}
            self.storage.db.execute('INSERT INTO projects VALUES(:id,:name,:path,:created)',project)
            return project

    def get(self,conversation):
        with self.storage.lock:
            row=self.storage.db.execute('SELECT * FROM chat_sessions WHERE conversation=?',(conversation,)).fetchone()
            return dict(row) if row else None

    def chats(self,project):
        with self.storage.lock:return [dict(r) for r in self.storage.db.execute('SELECT c.*,s.project,s.ordinal,s.workspace,s.kind FROM conversations c JOIN chat_sessions s ON c.id=s.conversation WHERE s.project=? ORDER BY s.ordinal',(project,))]

    def git(self,path,*args,check=True):
        result=subprocess.run(['git','-C',str(path),*args],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=90)
        if check and result.returncode:raise RuntimeError('Git no pudo preparar el worktree: '+result.stderr.decode('utf-8',errors='replace')[:300])
        return result

    def attach(self,conversation,project,isolated=True):
        with self.storage.lock:
            ordinal=self.storage.db.execute('SELECT COUNT(*) FROM chat_sessions').fetchone()[0]+1
            project_count=self.storage.db.execute('SELECT COUNT(*) FROM chat_sessions WHERE project=?',(project['id'],)).fetchone()[0]
        folder=self.root/f'chat-{ordinal:04d}';folder.mkdir(exist_ok=False)
        source=Path(project['path']);workspace=source;kind='original';branch=''
        try:
            if isolated and project_count:
                workspace=folder/'workspace'
                probe=self.git(source,'rev-parse','--show-toplevel',check=False) if shutil.which('git') else None
                if probe and probe.returncode==0:
                    repository=Path(probe.stdout.decode().strip()).resolve()
                    if repository!=source:raise ValueError('Elige la raíz del repositorio para crear worktrees')
                    branch='arise/chat-'+conversation[:12]
                    self.git(source,'worktree','add','-b',branch,str(workspace),'HEAD')
                    kind='worktree'
                    patch=self.git(source,'diff','--binary','HEAD').stdout
                    if patch:
                        applied=subprocess.run(['git','-C',str(workspace),'apply','--binary','-'],input=patch,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=90)
                        if applied.returncode:raise RuntimeError('No se pudieron copiar los cambios actuales al worktree')
                    for raw in self.git(source,'ls-files','--others','--exclude-standard','-z').stdout.split(b'\0'):
                        if not raw:continue
                        relative=Path(os.fsdecode(raw));item=source/relative;destination=workspace/relative
                        destination.parent.mkdir(parents=True,exist_ok=True)
                        if item.is_symlink():destination.symlink_to(os.readlink(item),target_is_directory=item.is_dir())
                        elif item.is_file():shutil.copy2(item,destination)
                else:
                    # Never recurse into the chat archive when it resides inside a project.
                    archive=self.root
                    def ignore(directory,names):
                        return [n for n in names if n=='.git' or (Path(directory)/n).resolve()==archive]
                    shutil.copytree(source,workspace,ignore=ignore,symlinks=True)
                    kind='copy'
            data={'conversation':conversation,'project':project['id'],'ordinal':ordinal,'folder':str(folder),'workspace':str(workspace),'kind':kind,'branch':branch}
            (folder/'session').mkdir()
            (folder/'preferences.json').write_text(json.dumps({key:self.storage.config[key] for key in PREFERENCES},indent=2),encoding='utf-8')
            (folder/'session.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            with self.storage.lock,self.storage.db:
                self.storage.db.execute('INSERT INTO chat_sessions VALUES(:conversation,:project,:ordinal,:folder,:workspace,:kind,:branch)',data)
                self.storage.db.execute('UPDATE conversations SET title=? WHERE id=?',(f'Chat {ordinal}',conversation))
            return data
        except Exception:
            if kind=='worktree':
                self.git(source,'worktree','remove','--force',str(workspace),check=False)
                self.git(source,'branch','-D',branch,check=False)
            shutil.rmtree(folder,ignore_errors=True)
            raise

    def checkpoint(self,conversation,session_file=None):
        data=self.get(conversation)
        if not data:return
        data.update(session_file=session_file,updated=time.time(),state='suspended')
        Path(data['folder'],'session.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        Path(data['folder'],'messages.json').write_text(json.dumps(self.storage.messages(conversation),ensure_ascii=False,indent=2),encoding='utf-8')
        self.save_preferences(conversation)

    def save_preferences(self, conversation):
        data=self.get(conversation)
        if data:Path(data['folder'],'preferences.json').write_text(json.dumps({key:self.storage.config[key] for key in PREFERENCES},indent=2),encoding='utf-8')

    def preferences(self,conversation):
        path=Path(self.get(conversation)['folder'],'preferences.json')
        if not path.is_file():return {}
        data=json.loads(path.read_text(encoding='utf-8'))
        return {key:value for key,value in data.items() if key in PREFERENCES}
