import copy
import json
import os.path
import threading
import typing


class SettingNull:
    __instance__ = None
    __lock__ = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            with cls.__lock__:
                if cls.__instance__ is None:
                    cls.__instance__ = super().__new__(cls)
                    cls.__instance__.__isInitialized__ = False
        return cls.__instance__


_null = SettingNull()


class Setting:
    __instance__ = None
    __lock__ = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            with cls.__lock__:
                if cls.__instance__ is None:
                    cls.__instance__ = super().__new__(cls)
                    cls.__instance__.__isInitialized__ = False
        return cls.__instance__

    def __init__(self, json_path: str):
        if self.__isInitialized__:
            return
        self.__isInitialized__ = True
        self.__data = {}
        self.__json_path = json_path
        self.__lock = threading.RLock()
        self.read(self.__json_path)

    @classmethod
    def data(cls):
        self = cls.__instance__ or cls()
        with self.__lock:
            return copy.deepcopy(self.__data)

    @classmethod
    def read(cls, json_path: str) -> bool:
        self = cls.__instance__ or cls()
        return self.__read_in_lock(json_path)

    def __read_in_lock(self, json_path: str) -> bool:
        if not os.path.exists(json_path):
            return False
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content:
                    return False
                data = json.loads(content)
                with self.__lock:
                    self.__data = data
                    self.__json_path = json_path
            return True
        except json.JSONDecodeError as e:
            _log.exception(f"JSON 解析错误: '{content}'")

            return False
        except Exception as e:
            _log.exception(f"读取配置失败: '{content}'")
            return False

    @classmethod
    def get(cls, key: str | tuple | list, default: typing.Any, *args, **kwargs) -> typing.Any:
        self = cls.__instance__ or cls()
        with self.__lock:
            search_dct = self.__data
            length = len(key) - 1
            need_write = False

            typ = type(default)

            if isinstance(key, (tuple, list)):
                for idx, k in enumerate(key):
                    is_last = (idx == length)

                    if k not in search_dct:
                        if is_last:
                            search_dct[k] = default
                        else:
                            search_dct[k] = {}
                        need_write = True
                        search_dct = search_dct[k]
                    else:
                        search_dct = search_dct[k]

                if typ is not typing.Any:
                    if not isinstance(search_dct, typ):
                        parent_dct = self.__data
                        for k in key[:-1]:
                            parent_dct = parent_dct[k]
                        parent_dct[key[-1]] = default
                        search_dct = default
                        need_write = True
            else:
                if key not in search_dct:
                    search_dct[key] = default
                    search_dct = search_dct[key]
                    need_write = True
                else:
                    search_dct = search_dct[key]

            if need_write:
                self.__write_in_lock()

            return search_dct

    @classmethod
    def set(cls, key: str | tuple | list, value: typing.Any, *args, **kwargs) -> bool:
        if len(key) == 0:
            raise ValueError("Setting.set: key 不能为空")

        self = cls.__instance__ or cls()
        need_write = False
        with self.__lock:
            search_dct = self.__data

            if isinstance(key, (tuple, list)):
                for k in key[:-1]:
                    if k not in search_dct:
                        search_dct[k] = {}
                    elif not isinstance(search_dct[k], dict):
                        _log.error(f"Setting.set: key '{k}' 已存在但不是 dict, 无法创建嵌套结构")
                        search_dct[k] = {}
                    search_dct = search_dct[k]
                if search_dct[key[-1]] != value:
                    search_dct[key[-1]] = value
                    need_write = True
            else:
                if search_dct[key] != value:
                    search_dct[key] = value
                    need_write = True

            if need_write:
                return self.__write_in_lock()
            else:
                return True

    def __write_in_lock(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.__json_path), exist_ok=True)

            with open(self.__json_path, 'w', encoding='utf-8') as f:
                json.dump(self.__data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            _log.exception(f"JSON 写入错误: {e}")
            return False

    @classmethod
    def exists(cls, *key: str) -> bool:
        self = cls.__instance__ or cls()

        with self.__lock:
            search_dct = self.__data
            for k in key:
                if k not in search_dct:
                    return False
                search_dct = search_dct[k]
            return True

    @classmethod
    def delete(cls, *key: str) -> bool:
        self = cls.__instance__ or cls()

        if len(key) == 0:
            return False

        with self.__lock:
            search_dct = self.__data

            for k in key[:-1]:
                if k not in search_dct:
                    return False
                search_dct = search_dct[k]

            if key[-1] in search_dct:
                del search_dct[key[-1]]
                return self.__write_in_lock()
            return False

    @classmethod
    def clear(cls) -> bool:
        self = cls.__instance__ or cls()

        with self.__lock:
            cls.__instance__.__data = {}
            return cls.__instance__.__write_in_lock()

    @classmethod
    def reload(cls) -> bool:
        self = cls.__instance__ or cls()
        return self.__read_in_lock(self.__json_path)
