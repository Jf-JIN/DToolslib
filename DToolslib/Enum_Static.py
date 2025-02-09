"""
常量枚举类

该枚举类支持唯一的枚举项, 且枚举项的值不能被修改.
枚举项访问方法为: 枚举类名.枚举项名
无需实例化, 也无需使用 枚举类名.枚举项名.value 获取枚举项的值
默认: 枚举项.name 为枚举项名, 但仅限于枚举项的类型为
    - `int`, `float`, `str`, `list`, `tuple`, `set`, `frozenset`, `dict`, `complex`, `bytes`, `bytearray`
"""


class _null:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __repr__(self):
        return '<class _null>'


_null = _null()

_object_attr = [
    '__new__', '__repr__', '__hash__', '__str__', '__getattribute__', '__setattr__', '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',
    '__init__', '__reduce_ex__', '__reduce__', '__getstate__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__', '__doc__',
    '__module__', '__qualname__', '__members__', 'isAllowedSetValue',
]


class _itemBase:
    def __init__(self, value):
        super().__init__()
        self.name = _null
        self.value = value
        self.string = _null

    def __setattr__(self, key: str, value):
        if value is _null:
            return
        if key in self.__dict__ or hasattr(self, f'_{self.__class__.__name__}__attr_lock'):
            raise AttributeError(f'Enumeration items are immutable and cannot be modified: <{key}> = {value}')
        super().__setattr__(key, value)


_analog_define_dict = {
    int: 'SEInteger',
    float: 'SEFloat',
    str: 'SEString',
    list: 'SEList',
    tuple: 'SETuple',
    set: 'SESet',
    frozenset: 'SEFrozenSet',
    dict: 'SEDictionary',
    complex: 'SEComplexNumber',
    bytes: 'SEBytes',
    bytearray: 'SEByteArray'
}

for type_, type_class in _analog_define_dict.items():
    globals()[type_class] = type(type_class, (type_, _itemBase), {})


class _StaticEnumDict(dict):
    """
    用于存储枚举项的字典类, 检查重复定义项
    """

    def __init__(self):
        super().__init__()
        self._cls_name = None
        self._member_names = {}

    def __setitem__(self, key, value):
        if key in self._member_names:
            raise ValueError(f'Enumeration item duplication: already exists\t< {key} > = {self._member_names[key]}')
        if (type(value) in _analog_define_dict) and key not in _object_attr:
            value = eval(f'{_analog_define_dict[type(value)]}({repr(value)})')
            value.name = key
        self._member_names[key] = value
        super().__setitem__(key, value)


class _StaticEnumMeta(type):
    """
    枚举类的元类
    """
    @classmethod
    def __prepare__(metacls, cls, bases, **kwds) -> _StaticEnumDict:
        """
        用于创建枚举项的字典类, 以便之后查找相同的枚举项
        """
        enum_dict = _StaticEnumDict()
        enum_dict._cls_name = cls
        return enum_dict

    def __new__(mcs, name, bases, dct: dict):
        if len(bases) == 0:
            return super().__new__(mcs, name, bases, dct)
        dct['__members__'] = {}  # 用于存储枚举项的字典
        dct['isAllowedSetValue'] = False  # 用于允许赋值枚举项的标志, 允许内部赋值, 禁止外部赋值
        members = {key: value for key, value in dct.items() if not key.startswith('__')}
        cls = super().__new__(mcs, name, bases, dct)
        for key, value in members.items():
            if key == 'isAllowedSetValue' or key == '__members__':
                continue
            elif isinstance(value, type) and not issubclass(value, StaticEnum) and value is not cls:
                original_bases = value.__bases__
                new_bases = (StaticEnum,) + original_bases
                new_cls = type(value.__name__, new_bases, dict(value.__dict__))
                setattr(cls, key, new_cls)
                continue
            cls.__members__['isAllowedSetValue'] = True
            cls.__members__[key] = value
            setattr(cls, key, value)
        if not hasattr(cls, '__allow_new_attr__') or not cls.__allow_new_attr__:
            for obj_name, obj in cls.__members__.items():
                if obj_name == 'isAllowedSetValue':
                    continue
                setattr(obj, f'_{obj.__class__.__name__}__attr_lock', None)
        return cls

    def __setattr__(cls, key, value):
        if key in cls.__members__ and not cls.__members__['isAllowedSetValue']:
            raise TypeError(f'Modification of the member "{key.__qualname__}" in the "{cls.__name__}" enumeration is not allowed. < {key.__qualname__} > = {cls.__members__[key]}')
        super().__setattr__(key, value)

    def __iter__(cls):
        return iter(cls.__members__.values())

    def __contains__(self, item) -> bool:
        return item in self.__members__.values()


class StaticEnum(metaclass=_StaticEnumMeta):
    """
    静态枚举类, 属性不可修改 Static enumeration class, attributes cannot be modified

    - 可以给枚举项添加属性, None和Boolean类型除外 You can add attributes to enumeration items except none and boolean types
    - 可以遍历, 使用keys(), 使用values(), 使用items() You can traverse, use keys(), use values(), and use items()
    """
    @classmethod
    def members(cls) -> list:
        cls.__members__: dict
        temp = []
        for key, value in cls.__members__.items():
            if key == 'isAllowedSetValue' or key == '__members__':
                continue
            temp.append((key, value))
        return temp

    def __hasattr__(self, item):
        return item in self.__members__.keys()

    def __getattr__(self, item):
        return self.__members__[item]

    def items(self):
        return self.__members__.items()

    def keys(self):
        return self.__members__.keys()

    def values(self):
        return self.__members__.values()


if __name__ == '__main__':
    class TestEnum(StaticEnum):
        A = '#ffffff'
        A.color_name = 'Red'
        A.ansi_font = 31
        A.ansi_background = 41

    print(TestEnum.A)  # output: #ffffff
    print(TestEnum.A.name)  # output: A
    print(TestEnum.A.color_name)  # output: Red
    print(TestEnum.A.ansi_font)  # output: 31
    print(type(TestEnum.A))  # output: <class '__main__.SEString'>
    print('#ffffff' in TestEnum)  # output: True
    print(isinstance(TestEnum.A, str))  # output: True
