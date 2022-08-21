import json
import os
import random
from pymongo import MongoClient

from discord import Message, Activity, ActivityType


class Config(dict):
    def __init__(self, storage_interface=None, loads=None):
        super().__init__()
        if storage_interface and not loads:
            super().__setattr__('storage', storage_interface)
            loads = storage_interface.load()
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
        self.storage.save(self)

    def reload(self):
        self.clear()
        self.__init__(self.storage)

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
    def __init__(self, loads:list=None):
        super().__init__()
        if loads:
            for value in loads:
                self._recursive_append(value)

    def __getitem__(self, keylist):
        if keylist == '.':
            return self
        elif isinstance(keylist, (int, slice)):
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

class FileStorage:
    def __init__(self, fp):
        self.fp = fp

    def save(self, data):
        with open(self.fp, 'w') as f:
            f.write(json.dumps(data))

    def load(self):
        with open(self.fp, 'r') as f:
            return json.loads(f.read())

    def __str__(self):
        return '<FileStorage @{}>'.format(self.fp)

class HerokuConfigVarsStorage:
    def __init__(self, var_name, secret):
        self.var_name = var_name
        self.secret = secret
        raise NotImplementedError

    def save(self, data):
        pass

    def load(self):
        pass

    def __str__(self):
        return '<HerokuConfigVarsStorage @{}>'.format(self.var_name)

class MongoStorage:
    collection = None

    def __init__(self, user, secret, _id):
        if MongoStorage.collection is None:
            # Reuse blurbot collection client for other MongoStorage instances
            MongoStorage.collection = MongoClient(
                "mongodb+srv://{}:{}@cluster0.cbjbjyq.mongodb.net/?retryWrites=true&w=majority"
                .format(user, secret)
            )['discord']['blurbot']
        self._id = _id

    def save(self, data):
        data['_id'] = self._id
        self.collection.update_one(
            {'_id': self._id}, {'$set': data},
            upsert=True
        )

    def load(self):
        return self.collection.find_one({'_id': self._id}) or {}

    def __str__(self):
        return '<MongoStorage {} @{}>'.format(self._id, self.collection.name)

def create_storage(label):
    storage_type = os.environ['BLURBOT_STORAGE_INTERFACE']
    if storage_type == 'file':
        return FileStorage(os.environ['FILEPATH_' + label.upper()])
    elif storage_type == 'heroku':
        return HerokuConfigVarsStorage(
            os.environ['HEROKU_VARNAME_' + label.upper()],
            os.environ['HEROKU_SECRET']
        )
    elif storage_type == 'mongo':
        return MongoStorage(
            os.environ['MONGO_USER'],
            os.environ['MONGO_SECRET'],
            label
        )
    else:
        raise ValueError('Invalid storage interface: ' + storage_type)


def render_egg(egg, msg:Message):
    if egg.startswith('#eval '):
        egg = egg.lstrip('#eval ')
        egg = eval(egg, {'__builtins__': None}, {'msg': msg, 'rand': random.random})
    return egg

def get_presence(presence):
    return Activity(type=ActivityType[presence.activity], name=presence.name)


class VoiceError(Exception):
    pass
