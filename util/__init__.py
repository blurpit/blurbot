import json
import random

from discord import Message, Activity, ActivityType


class Config(dict):
    def __init__(self, *, loads:dict=None, fp=None):
        super().__init__()
        if fp:
            self.fp = fp
            with open(fp, 'r') as f:
                loads = json.loads(f.read())
        if loads:
            for key, value in loads.items():
                self._recursive_add(key, value)

    def __getitem__(self, keylist):
        if keylist == '.':
            return self

        keylist = keylist.split('.', 1)
        val = super().__getitem__(keylist[0])
        if len(keylist) > 1:
            val = val[keylist[1]]
        return val

    def __setitem__(self, keylist, value):
        keylist = keylist.split('.', 1)
        if len(keylist) == 1:
            super().__setitem__(keylist[0], value)
        else:
            val = super().__getitem__(keylist[0])
            val[keylist[1]] = value

    def __getattr__(self, key):
        return super().__getitem__(key)

    def __setattr__(self, key, value):
        super().__setitem__(key, value)

    def __str__(self):
        return json.dumps(self, indent=4)

    def _recursive_add(self, key, value):
        key = self.infer_type(key)
        if isinstance(value, dict):
            self[key] = Config(loads=value)
        elif isinstance(value, list):
            self[key] = ConfigList(loads=value)
        else:
            self[key] = value

    def save(self):
        if getattr(self, 'fp', None):
            with open(self.fp, 'w') as f:
                f.write(json.dumps(self, indent=4))

    def reload(self):
        fp = self.fp
        self.clear()
        self.__init__(fp=fp)

    @staticmethod
    def infer_type(val:str):
        if val.lower() == 'none': return None
        elif val.lower() == 'true': return True
        elif val.lower() == 'false': return False
        elif val == '[]': return ConfigList()
        elif val == '{}': return Config()

        try: # test if key is number
            val = float(val)
            if val % 1 == 0: val = int(val)
        except ValueError:
            pass

        return val

class ConfigList(list):
    def __init__(self, *, loads:list=None):
        super().__init__()
        if loads:
            for value in loads:
                self._recursive_append(value)

    def __getitem__(self, keylist):
        if keylist == '.':
            return self
        elif isinstance(keylist, int):
            return super().__getitem__(keylist)

        keylist = keylist.split('.', 1)
        val = super().__getitem__(int(keylist[0]))
        if len(keylist) > 1:
            val = val[keylist[1]]
        return val

    def __setitem__(self, keylist, value):
        if isinstance(keylist, int):
            super().__setitem__(keylist, value)
        elif keylist == 'append':
            super().append(value)
        elif keylist == 'remove':
            super().remove(value)
        elif keylist == 'removei':
            super().__delitem__(value)
        else:
            keylist = keylist.split('.', 1)
            if len(keylist) == 1:
                super().__setitem__(int(keylist[0]), value)
            else:
                val = super().__getitem__(int(keylist[0]))
                val[keylist[1]] = value

    def __str__(self):
        return json.dumps(self, indent=4)

    def _recursive_append(self, value):
        if isinstance(value, dict):
            self.append(Config(loads=value))
        elif isinstance(value, list):
            self.append(ConfigList(loads=value))
        else:
            self.append(value)

def load_token():
    with open('data/client_secret.txt', 'r') as secret:
        return secret.read().strip()

def render_egg(egg, msg:Message):
    if egg.startswith('#eval '):
        egg = egg.lstrip('#eval ')
        egg = eval(egg, {'__builtins__': None}, {'msg': msg, 'rand': random.random})
    return egg

def get_presence(presence):
    return Activity(type=ActivityType[presence.activity], name=presence.name)
