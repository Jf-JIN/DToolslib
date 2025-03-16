"""
常量枚举类

该枚举类支持唯一的枚举项, 且枚举项的值不能被修改.
枚举项访问方法为: 枚举类名.枚举项名
无需实例化, 也无需使用 枚举类名.枚举项名.value 获取枚举项的值
默认: 枚举项.name 为枚举项名, 但仅限于枚举项的类型为
    - `int`, `float`, `str`, `list`, `tuple`, `set`, `frozenset`, `dict`, `complex`, `bytes`, `bytearray`
"""
__all__ = ['StaticEnum']


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
        if key == f'_{self.__class__.__name__}__attr_lock' and hasattr(self, f'_{self.__class__.__name__}__attr_lock') and getattr(self, f'_{self.__class__.__name__}__attr_lock'):
            return
        if (key in self.__dict__ and key != f'_{self.__class__.__name__}__attr_lock') or (hasattr(self, f'_{self.__class__.__name__}__attr_lock')):
            raise AttributeError(f'Enumeration items are immutable and cannot be modified: <{key}> = {value}')
        super().__setattr__(key, value)


class _SEInteger(int, _itemBase):
    pass


class _SEFloat(float, _itemBase):
    pass


class _SEString(str, _itemBase):
    pass


class _SEList(list, _itemBase):
    pass


class _SETuple(tuple, _itemBase):
    pass


class _SESet(set, _itemBase):
    pass


class _SEFrozenSet(frozenset, _itemBase):
    pass


class _SEDictionary(dict, _itemBase):
    pass


class _SEComplexNumber(complex, _itemBase):
    pass


class _SEBytes(bytes, _itemBase):
    pass


class _SEByteArray(bytes, _itemBase):
    pass


_analog_define_dict = {
    int: _SEInteger,
    float: _SEFloat,
    str: _SEString,
    list: _SEList,
    tuple: _SETuple,
    set: _SESet,
    frozenset: _SEFrozenSet,
    dict: _SEDictionary,
    complex: _SEComplexNumber,
    bytes: _SEBytes,
    bytearray: _SEByteArray
}


class _StaticEnumDict(dict):
    """
    用于存储枚举项的字典类, 检查重复定义项
    """

    def __init__(self):
        super().__init__()
        self._cls_name = None
        self._member_names = {}

    def __setitem__(self, key: str, value):
        if key in self._member_names:
            raise ValueError(f'Enumeration item duplication: already exists\t< {key} > = {self._member_names[key]}')
        if (type(value) in _analog_define_dict) and key not in _object_attr and not (key.startswith('__') and key.endswith('__')):
            # 默认所有 __名称__ 的属性都是类的重要属性, 不能被枚举项占用
            value = _analog_define_dict[type(value)](value)
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
        def _convert_to_enum_item(cls, key, value):
            cls_dict = dict(value.__dict__)
            flag_allow_new_attr = False
            for sub_key, sub_value in cls_dict.items():
                if isinstance(sub_value, type) and not issubclass(sub_value, StaticEnum) and sub_value is not value:
                    _convert_to_enum_item(sub_value, sub_key, sub_value)
                if sub_key not in _object_attr and not (sub_key.startswith('__') and sub_key.endswith('__')) and type(sub_value) in _analog_define_dict:
                    cls_dict[sub_key] = _analog_define_dict[type(sub_value)](sub_value)
                    cls_dict[sub_key].name = sub_key
                    if hasattr(cls, '__allow_new_attr__') and cls.__allow_new_attr__:
                        flag_allow_new_attr = True
            if flag_allow_new_attr:
                cls_dict['__allow_new_attr__'] = True
            new_cls = type(
                value.__name__,
                (StaticEnum,),
                cls_dict
            )
            setattr(cls, key, new_cls)

        def _recursion_set_attr_lock(cls):
            for obj_name, obj in cls.__members__['data'].items():
                if isinstance(obj, _StaticEnumMeta):
                    _recursion_set_attr_lock(obj)
                    continue
                setattr(obj, f'_{obj.__class__.__name__}__attr_lock', True)

        if len(bases) == 0:
            return super().__new__(mcs, name, bases, dct)
        dct['__members__'] = {  # 用于存储枚举项的字典
            'isAllowedSetValue': False,  # 用于允许赋值枚举项的标志, 允许内部赋值, 禁止外部赋值
            'data': {}  # 用于存储枚举项的值
        }
        members = {key: value for key, value in dct.items() if not key.startswith('__')}
        cls = super().__new__(mcs, name, bases, dct)
        for key, value in members.items():
            if key == 'isAllowedSetValue' or key == '__members__':
                continue
            elif isinstance(value, type) and not issubclass(value, StaticEnum) and value is not cls:
                _convert_to_enum_item(cls, key, value)
                continue
            cls.__members__['isAllowedSetValue'] = True
            cls.__members__['data'][key] = value
            setattr(cls, key, value)
        if not hasattr(cls, '__allow_new_attr__') or not cls.__allow_new_attr__:
            _recursion_set_attr_lock(cls)
        cls.__members__['isAllowedSetValue'] = False
        return cls

    def __setattr__(cls, key, value):
        if key in cls.__members__['data'] and not cls.__members__['isAllowedSetValue']:
            ori = cls.__members__['data'][key]
            raise TypeError(f'Modification of the member "{key.__qualname__}" in the "{cls.__name__}" enumeration is not allowed. < {key.__qualname__} > = {ori}')
        elif key not in cls.__members__ and not isinstance(value, type) and '__attr_lock' not in key and not cls.__members__['isAllowedSetValue']:
            raise TypeError(f'Addition of the member "{key}" in the "{cls.__name__}" enumeration is not allowed.')
        super().__setattr__(key, value)

    def __iter__(cls):
        return iter(cls.__members__['data'].values())

    def __contains__(self, item) -> bool:
        return item in self.__members__['data'].values()


class StaticEnum(metaclass=_StaticEnumMeta):
    """
    静态枚举类, 属性不可修改 Static enumeration class, attributes cannot be modified

    - 可以给枚举项添加属性, None和Boolean类型除外 You can add attributes to enumeration items except none and boolean types
    - 可以遍历, 使用keys(), 使用values(), 使用items() You can traverse, use keys(), use values(), and use items()

    如果枚举类含有__allow_new_attr__属性, 则允许枚举类外部给枚举项添加新的属性, 例如: 
    If the enumeration class contains the __allow_new_attr__ attribute, it is allowed to add new attributes to enumeration items outside the enumeration class, for example:

    class MyEnum(StaticEnum):
        __allow_new_attr__ = True
        A = 1
        B = 2

    MyEnum.A.new_attr = 3 # No Error, else Error will occur.


    """
    @classmethod
    def members(cls) -> list:
        temp = []
        for key, value in cls.__members__['data'].items():
            temp.append((key, value))
        return temp

    def __hasattr__(self, item):
        return item in self.__members__['data'].keys()

    def __getattr__(self, item):
        return self.__members__['data'][item]

    def items(self):
        return self.__members__['data'].items()

    def keys(self):
        return self.__members__['data'].keys()

    def values(self):
        return self.__members__['data'].values()

    @classmethod
    def getItem(cls, item):
        for key, value in cls.__members__['data'].items():
            if value == item:
                return value
        raise AttributeError(f'Item {item} not found in {self.__class__.__name__}')


""" 
if __name__ == '__main__':
    class TestEnum(StaticEnum):
        A = '#ff0000'
        A.color_name = 'Red'
        A.ansi_font = 31
        A.ansi_background = 41

    print(TestEnum.A)  # output: #ff0000
    print(TestEnum.A.name)  # output: A
    print(TestEnum.A.color_name)  # output: Red
    print(TestEnum.A.ansi_font)  # output: 31
    print(type(TestEnum.A))  # output: <class '__main__.SEString'>
    print('#ff0000' in TestEnum)  # output: True
    print(isinstance(TestEnum.A, str))  # output: True
"""
