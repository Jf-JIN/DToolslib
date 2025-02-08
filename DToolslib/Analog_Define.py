"""
常量枚举类

该枚举类支持唯一的枚举项, 且枚举项的值不能被修改.
枚举项访问方法为: 枚举类名.枚举项名
无需实例化, 也无需使用 枚举类名.枚举项名.value 获取枚举项的值
默认: 枚举项.name 为枚举项名, 但仅限于枚举项的类型为
    - `int`, `float`, `str`, `list`, `tuple`, `set`, `frozenset`, `dict`, `complex`, `bytes`, `bytearray`
"""


class _null:
    def __repr__(self):
        return '< class _null >'


_null = _null()


class _itemBase:
    def __init__(self, value):
        super().__init__()
        self.name = _null
        self.value = value
        self.string = _null

    def __setattr__(self, key: str, value):
        if value is _null:
            return
        if key in self.__dict__:
            raise AttributeError(f'禁止修改枚举项\t< {key} > = {value}')
        super().__setattr__(key, value)


_analog_define_dict = {
    int: 'ADInteger',
    float: 'ADFloat',
    str: 'ADString',
    list: 'ADList',
    tuple: 'ADTuple',
    set: 'ADSet',
    frozenset: 'ADFrozenSet',
    dict: 'ADDictionary',
    complex: 'ADComplexNumber',
    bytes: 'ADBytes',
    bytearray: 'ADByteArray'
}

for type_, type_class in _analog_define_dict.items():
    globals()[type_class] = type(type_class, (type_, _itemBase), {})


class _AnalogDefineDict(dict):
    """
    用于存储枚举项的字典类, 检查重复定义项
    """

    def __init__(self):
        super().__init__()
        self.cls_name = None
        self._member_names = {}

    def __setitem__(self, key, value):
        if key in self._member_names:
            raise ValueError(f'枚举项重复: 已存在\t< {key} > = {self._member_names[key]}')
        if type(value) in _analog_define_dict and key not in ['__module__', '__qualname__', '_members_', 'isAllowedSetValue']:
            value = eval(f'{_analog_define_dict[type(value)]}({repr(value)})')
            value.name = key
        self._member_names[key] = value
        super().__setitem__(key, value)


class _AnalogDefineMeta(type):
    """
    枚举类的元类
    """
    @classmethod
    def __prepare__(metacls, cls, bases, **kwds) -> _AnalogDefineDict:
        """
        用于创建枚举项的字典类, 以便之后查找相同的枚举项
        """
        enum_dict = _AnalogDefineDict()
        enum_dict._cls_name = cls
        return enum_dict

    def __new__(mcs, name, bases, dct: dict):
        if len(bases) == 0:
            return super().__new__(mcs, name, bases, dct)
        dct['_members_'] = {}  # 用于存储枚举项的字典
        dct['isAllowedSetValue'] = False  # 用于允许赋值枚举项的标志, 允许内部赋值, 禁止外部赋值
        members = {key: value for key, value in dct.items() if not key.startswith('__')}
        cls = super().__new__(mcs, name, bases, dct)
        for key, value in members.items():
            if key == 'isAllowedSetValue' or key == '_members_':
                continue
            elif isinstance(value, type) and not issubclass(value, AnalogDefine) and value is not cls:
                original_bases = value.__bases__
                new_bases = (AnalogDefine,) + original_bases
                new_cls = type(value.__name__, new_bases, dict(value.__dict__))
                setattr(cls, key, new_cls)
                continue
            cls._members_['isAllowedSetValue'] = True
            cls._members_[key] = value
            setattr(cls, key, value)
            cls._members_['isAllowedSetValue'] = False
        return cls

    def __setattr__(cls, key, value):
        if key in cls._members_ and not cls._members_['isAllowedSetValue']:
            raise AttributeError(f'禁止修改枚举项\t< {key.__qualname__} > = {cls._members_[key]}')
        super().__setattr__(key, value)


class AnalogDefine(metaclass=_AnalogDefineMeta):
    @classmethod
    def members(cls):
        temp = []
        for key, value in cls._members_.items():
            if key == 'isAllowedSetValue' or key == '_members_':
                continue
            temp.append((key, value))
        return temp

    def __contains__(self, item):
        return item in self._members_.keys()

    def __hasattr__(self, item):
        return item in self._members_.keys()

    def __getattr__(self, item):
        return self._members_[item]

    def items(self):
        return self._members_.items()

    def keys(self):
        return self._members_.keys()

    def values(self):
        return self._members_.values()


if __name__ == '__main__':
    class Test(AnalogDefine):
        A = 1
        B = 2.0
        C = '3 5'
        D = [4, 'F F', 5.655, [5, 'p'], {'a': 'b 1'}, {'f', 'ds'}]
        F = {5}
        G = {'g': 6}
    print(Test.A)
    print(Test.A.name)
    print(type(Test.A))
