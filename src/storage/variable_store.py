class VariableStore:
    _store = {}

    @classmethod
    def set(cls, key, value):
        cls._store[key] = value

    @classmethod
    def get(cls, key, default=None):
        return cls._store.get(key, default)

    @classmethod
    def exists(cls, key):
        return key in cls._store

    @classmethod
    def remove(cls, key):
        cls._store.pop(key, None)

global_variable = VariableStore()
