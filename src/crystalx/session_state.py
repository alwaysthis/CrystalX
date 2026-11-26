"""Persistent local navigation state, separate from application defaults."""
import json
import logging
from pathlib import Path

class SessionState:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path(__file__).resolve().parents[2]/'config/custom/session.json'
        self.directory=''
        if self.path.exists():
            try:
                data=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data,dict): raise ValueError('Session state must be an object')
                value=data.get('last_open_directory','')
                if isinstance(value,str) and Path(value).is_dir(): self.directory=value
            except (OSError,ValueError) as error: logging.getLogger(__name__).warning('Cannot read session state: %s',error)

    def opened(self,path):
        directory=str(Path(path).resolve().parent)
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp'); temporary.write_text(json.dumps({'last_open_directory':directory},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); temporary.replace(self.path)
        except OSError:
            logging.getLogger(__name__).exception('Cannot persist last open directory')
        self.directory=directory
