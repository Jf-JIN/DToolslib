"""
常量枚举类

该枚举类支持唯一的枚举项, 且枚举项的值不能被修改.
枚举项访问方法为: 枚举类名.枚举项名
无需实例化, 也无需使用 枚举类名.枚举项名.value 获取枚举项的值
默认: 枚举项.name 为枚举项名, 但仅限于枚举项的类型为
    - `int`, `float`, `str`, `list`, `tuple`, `set`, `frozenset`, `dict`, `complex`, `bytes`, `bytearray`
"""
__all__ = ['StaticEnum']

import json
import sys

from .Color_Text import ansi_color_text


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
    '__new__', '__repr__', '__call__', '__hash__', '__str__', '__getattribute__', '__setattr__', '__delattr__',
    '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',
    '__init__', '__or__', '__ror__', 'mro', '__subclasses__', '__prepare__', '__instancecheck__', '__subclasscheck__',
    '__reduce_ex__', '__reduce__', '__getstate__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__',
    '__basicsize__', '__dir__', '__class__', '__doc__', '__itemsize__', '__flags__', '__weakrefoffset__',
    '__module__', '__qualname__', '__SE_members__', '__base__', '__dictoffset__', '__mro__', '__name__',
    '__abstractmethods__', '__bases__', '__dict__', '__text_signature__', '__annotations__', '__isAllowedSetValue__',
    '__enable_member_attribute__', '__enable_member_extension__', '__int_enums__',
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
        if key == f'_{self.__class__.__name__}__attr_lock' and hasattr(self,
                                                                       f'_{self.__class__.__name__}__attr_lock') and getattr(
            self, f'_{self.__class__.__name__}__attr_lock'):
            return
        if (key in self.__dict__ and key != f'_{self.__class__.__name__}__attr_lock') or (
                hasattr(self, f'_{self.__class__.__name__}__attr_lock')):
            error_text = f'Enumeration items are immutable and cannot be modified: <{key}> = {value}'
            raise AttributeError(ansi_color_text(error_text, 33))
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


_static_enum_dict = {
    int      : _SEInteger,
    float    : _SEFloat,
    str      : _SEString,
    list     : _SEList,
    tuple    : _SETuple,
    set      : _SESet,
    frozenset: _SEFrozenSet,
    dict     : _SEDictionary,
    complex  : _SEComplexNumber,
    bytes    : _SEBytes,
    bytearray: _SEByteArray
}


class _StaticEnumDict(dict):
    def __init__(self, enable_repeatable: bool, enable_member_attribute: bool, enable_member_extension: bool,
                 enum_value_mode: int) -> None:
        super().__init__()
        self._cls_name = None
        self._member_names: dict = {}
        self._enable_repeatable: bool = enable_repeatable
        self._enable_member_attribute: bool = enable_member_attribute
        self._enable_member_extension: bool = enable_member_extension
        self._enum_value_mode: int = enum_value_mode
        self._int_enums: dict = {}
        self.__setitem__('__enable_repeatable__', self._enable_repeatable)
        self.__setitem__('__enable_member_attribute__', self._enable_member_attribute)
        self.__setitem__('__enable_member_extension__', self._enable_member_extension)
        self.__setitem__('__enum_value_mode__', self._enum_value_mode)
        self.__setitem__('__enum_int_num__', -1)
        self.__setitem__('__int_enums__', self._int_enums)

    def __setitem__(self, key: str, value) -> None:
        if key in self._member_names:
            error_text = f'Enumeration item duplication: already exists\t< {key} > = {self._member_names[key]}'
            raise ValueError(ansi_color_text(error_text, 33))
        # 替换枚举项的类型, 增加扩展性
        if self._enable_member_attribute and (type(value) in _static_enum_dict) and key not in _object_attr and not (
                key.startswith('__') and key.endswith('__')):
            # 默认所有 __名称__ 的属性都是类的重要属性, 不能被枚举项占用
            # 判断条件: 允许使用枚举项属性 && 类型属于常规数据类型 && 枚举项名称不在对象属性中 && 枚举项名称不是 __名称__ 形式
            value = _static_enum_dict[type(value)](value)
            value.name = key
        # 记录整数枚举项, 用于后续自动赋值整型枚举项
        if type(value) == _SEInteger:
            self._int_enums[key] = value.value
        elif type(value) == int:
            self._int_enums[key] = value
        # 记录枚举项, 用于后续禁止重复定义
        self._member_names[key] = value
        super().__setitem__(key, value)


class _StaticEnumMeta(type):
    @classmethod
    def __prepare__(metacls, cls, bases, enable_repeatable: bool = True, enable_member_attribute: bool = False,
                    enable_member_extension: bool = False,
                    enum_value_mode: bool = False, *args, **kwargs) -> _StaticEnumDict:
        # print(f'prepare - {cls}: {enable_member_attribute}, {enable_member_extension}, {enum_value_mode}')
        if (enable_member_attribute or enable_member_extension) and enum_value_mode != 0:
            warning_text = ansi_color_text(
                f'<StaticEnum -> {cls}> enable_member_attribute and enum_value_mode are mutually exclusive, please choose one. Otherwise, the enable_member_attribute will be invalid.',
                33)
            sys.stdout.write(warning_text)
        if enable_member_extension and not enable_member_attribute:
            warning_text = ansi_color_text(
                f'<StaticEnum -> {cls}> befor enable_member_attribute, please enable enable_member_extension first. Otherwise, the enable_member_attribute will be invalid.',
                33)
            sys.stdout.write(warning_text)
        enum_dict = _StaticEnumDict(enable_repeatable, enable_member_attribute, enable_member_extension,
                                    enum_value_mode)
        enum_dict._cls_name = cls
        return enum_dict

    def __new__(mcs, name, bases, dct: dict, *args, **kwargs):
        def __init_cls_dct() -> dict:
            # 用于存储枚举项的字典
            return {
                'isAllowedSetValue' : False,  # 用于允许赋值枚举项的标志, 允许内部赋值, 禁止外部赋值
                'all_members'       : {},  # 用于存储全部枚举项的值
                'value_registry_map': {},  # 用于检查是否值重复
                'own_members'       : {},  # 本类自身定义的枚举项
                'alias_members'     : {},  # 子枚举透传过来的枚举项
            }

        def _get_enum_int_value(cls, key, value, isInt=True) -> int | str:
            if hasattr(value, '__qualname__') and "." in value.__qualname__:
                return value
            ori_lock_status = cls.__SE_members__['isAllowedSetValue']
            cls.__SE_members__['isAllowedSetValue'] = True
            while True:
                cls.__enum_int_num__ += 1
                if cls.__enum_int_num__ not in cls.__int_enums__.values():
                    cls.__int_enums__[key] = cls.__enum_int_num__
                    if isInt:
                        cls.__SE_members__['isAllowedSetValue'] = ori_lock_status
                        return cls.__enum_int_num__
                    else:
                        cls.__SE_members__['isAllowedSetValue'] = ori_lock_status
                        return str(cls.__enum_int_num__)

        def _convert_to_enum_item(root_cls, key, value,
                                  enable_repeatable: bool,
                                  enable_member_attribute: bool,
                                  enable_member_extension: bool,
                                  enum_value_mode: int,
                                  *args, **kwargs):
            cls_dict = dict(value.__dict__)
            cls_dict.pop('__dict__', None)
            cls_dict.pop('__weakref__', None)
            cls_dict['__module__'] = value.__module__
            cls_dict['__qualname__'] = f'{root_cls.__qualname__}.{key}'
            cls_dict['__enable_repeatable__'] = enable_repeatable
            cls_dict['__enable_member_attribute__'] = enable_member_attribute
            cls_dict['__enable_member_extension__'] = enable_member_extension
            cls_dict['__enum_value_mode__'] = enum_value_mode
            cls_dict['__int_enums__'] = {}
            cls_dict['__enum_int_num__'] = -1
            cls_dict['__SE_members__'] = __init_cls_dct()

            for sub_key, sub_value in list(cls_dict.items()):
                if (isinstance(sub_value, type)
                        and not issubclass(sub_value, StaticEnum)
                        and sub_value is not value):
                    new_sub = _convert_to_enum_item(
                        root_cls,
                        sub_key,
                        sub_value,
                        enable_repeatable,
                        enable_member_attribute,
                        enable_member_extension,
                        enum_value_mode
                    )
                    cls_dict[sub_key] = new_sub

                if (enable_member_attribute
                        and sub_key not in _object_attr
                        and not (sub_key.startswith('__') and sub_key.endswith('__'))
                        and type(sub_value) in _static_enum_dict):
                    if enum_value_mode == 1:
                        sub_value = _get_enum_int_value(root_cls, sub_key, sub_value, isInt=True)
                    elif enum_value_mode == 2:
                        sub_value = _get_enum_int_value(root_cls, sub_key, sub_value, isInt=False)
                    cls_dict[sub_key] = _static_enum_dict[type(sub_value)](sub_value)
                    cls_dict[sub_key].name = sub_key

            new_cls = _StaticEnumMeta(
                value.__name__,
                (StaticEnum,),
                cls_dict
            )

            if not hasattr(root_cls, '__SE_members__'):
                root_cls.__SE_members__ = __init_cls_dct()
            ori_lock = root_cls.__SE_members__['isAllowedSetValue']
            root_cls.__SE_members__['isAllowedSetValue'] = True
            try:
                type.__setattr__(root_cls, key, new_cls)
            finally:
                root_cls.__SE_members__['isAllowedSetValue'] = ori_lock

            root_cls.__SE_members__['all_members'][key] = new_cls
            return new_cls

        def _recursion_set_attr_lock(cls):
            for obj_name, obj in cls.__SE_members__['all_members'].items():
                if isinstance(obj, _StaticEnumMeta):
                    _recursion_set_attr_lock(obj)
                    continue
                if type(obj) not in _static_enum_dict.values():
                    continue
                setattr(obj, f'_{obj.__class__.__name__}__attr_lock', True)

        if len(bases) == 0:
            return super().__new__(mcs, name, bases, dct)
        dct['__SE_members__'] = __init_cls_dct()

        members = {key: value for key, value in dct.items() if not key.startswith('__')}
        cls = super().__new__(mcs, name, bases, dct)
        for key, value in members.items():
            if key == 'isAllowedSetValue' or key == '__SE_members__':
                continue
            elif isinstance(value, type) and not issubclass(value, StaticEnum) and value is not cls:
                new_cls = _convert_to_enum_item(cls, key, value, dct['__enable_repeatable__'],
                                                dct['__enable_member_attribute__'],
                                                dct['__enable_member_extension__'], dct['__enum_value_mode__'])
                cls.__SE_members__['own_members'][key] = new_cls
                continue
            cls.__SE_members__['isAllowedSetValue'] = True
            if cls.__enum_value_mode__ == 1:
                value = _get_enum_int_value(cls, key, value, isInt=True)
            elif cls.__enum_value_mode__ == 2:
                value = _get_enum_int_value(cls, key, value, isInt=False)
            cls.__SE_members__['all_members'][key] = value
            cls.__SE_members__['own_members'][key] = value
            setattr(cls, key, value)

        if '__annotations__' in dct:
            ori_lock_status = cls.__SE_members__['isAllowedSetValue']
            cls.__SE_members__['isAllowedSetValue'] = True
            for key, value in dct['__annotations__'].items():
                if value == int:
                    if cls.__enable_member_attribute__:
                        item = _SEInteger(_get_enum_int_value(cls, key, value))
                        item.name = key
                    else:
                        item = _get_enum_int_value(cls, key, value)
                    cls.__SE_members__['all_members'][key] = item
                    cls.__SE_members__['own_members'][key] = item
                    setattr(cls, key, item)
                else:
                    match_text = ansi_color_text(f'{name} -> {key}: {value}', 36)
                    error_text = ansi_color_text(f'Warning: ', 33) + match_text + \
                                 ansi_color_text(
                                     '\nStaticEnum only supports int type members without default values. For other types, please assign a default value explicitly.\n',
                                     33)
                    sys.stdout.write(error_text)
            cls.__SE_members__['isAllowedSetValue'] = ori_lock_status
        if cls.__enable_member_attribute__ and cls.__enable_member_extension__:
            _recursion_set_attr_lock(cls)
        cls.__SE_members__['isAllowedSetValue'] = False

        for k, v in cls.__SE_members__['value_registry_map'].items():
            if len(v) > 1:
                key_value_str = ', '.join([f'{var}={k}' for var in v])
                error_text = f'Repeat key-value pairs: {key_value_str}'
                raise TypeError(ansi_color_text(error_text, 33))
        return cls

    @classmethod
    def __is_hashable(cls, obj) -> bool:
        try:
            hash(obj)
            return True
        except TypeError:
            return False

    def __setattr__(cls, key, value):
        if key in cls.__SE_members__['all_members'] and not cls.__SE_members__['isAllowedSetValue']:
            ori = cls.__SE_members__['all_members'][key]
            error_text = f'Modification of the member "{key}" in the "{cls.__name__}" enumeration is not allowed. < {key} > = {ori}'
            raise TypeError(ansi_color_text(error_text, 33))
        elif key not in cls.__SE_members__ and not isinstance(value, type) and '__attr_lock' not in key and not \
                cls.__SE_members__['isAllowedSetValue']:
            error_text = f'Addition of the member "{key}" in the "{cls.__name__}" enumeration is not allowed.'
            raise TypeError(ansi_color_text(error_text, 33))
        if key in cls.__SE_members__['all_members'] and cls.__is_hashable(value) and not cls.__enable_repeatable__:
            if value is not None and not isinstance(value, bool):
                if value not in cls.__SE_members__['value_registry_map']:
                    cls.__SE_members__['value_registry_map'][value] = []
                cls.__SE_members__['value_registry_map'][value].append(key)
        # cls.__SE_members__['own_members'][key] = value
        super().__setattr__(key, value)

    def __str__(cls):
        items = list(cls.__SE_members__['own_members'].items())
        header = f"\n<StaticEnum> '{cls.__module__}.{cls.__name__}'"
        lines = [ansi_color_text(header, txt_color=33)]
        for i, (k, v) in enumerate(items):
            index = ansi_color_text(i, txt_color=32)
            type_t = ansi_color_text(type(v).__name__, txt_color=34)
            key = ansi_color_text(k, txt_color=36, bold=True)
            if isinstance(v, str):
                v = "'" + v + "'"
            value = ansi_color_text(v, txt_color=36, italic=True)
            lines.append(f"{index:<5} | {type_t:<15} | {key:<30} | {value}")
        return "\n".join(lines) + '\n'

    def __repr__(cls):
        return f"{cls.__name__}: {cls.__SE_members__['all_members']}"

    def __iter__(cls):
        return iter(cls.__SE_members__['all_members'].values())

    def __contains__(self, item) -> bool:
        return item in self.__SE_members__['all_members'].keys()


class StaticEnum(metaclass=_StaticEnumMeta, enable_repeatable=True, enable_member_attribute=False,
                 enable_member_extension=False,
                 enum_value_mode=0):
    """
    StaticEnum is a static enumeration class with enhanced enum member capabilities,
    implemented via the custom metaclass `_StaticEnumMeta`.

    Features:
    - Enum members are immutable (static behavior).
    - Unassigned `int`-typed declarations like `X: int` will be auto-assigned incrementing integer values starting from 0.
    - Enum members can hold additional attributes (if `enable_member_attribute` is enabled).
    - Members can be extended outside class definition (if `enable_member_extension` is enabled).
    - Supports iteration and access via `keys()`, `values()`, `items()`.
    - No type conversion is applied to magic attributes, `None`, or booleans — so they do not support extra attributes.
    - Nested classes are automatically converted into StaticEnum subclasses.

    Class-level Parameters (received by metaclass):
    - enable_member_attribute: bool
        Enable attribute binding on enum members. If True, allows `MyEnum.A.some_attr = 123`.
        Also, each enum member automatically gets two built-in attributes: `name` and `value`,
        where `name` stores the member's identifier (e.g., `'A'`), and `value` stores its assigned value.

    - enable_member_extension: bool
        Allow enum members to be extended with attributes outside the class definition.

    Methods:
    - cls.members() -> list[(key, value)]
        Returns all enum members as a list of (key, value) pairs.

    - cls.items() -> dict_items
        Returns a view of all enum items (key-value pairs).

    - cls.keys() -> dict_keys
        Returns a view of all enum keys.

    - cls.values() -> dict_values
        Returns a view of all enum values.

    - cls.getItemByValue(value) -> EnumMember
        Find enum member by value; raise AttributeError if not found.


    StaticEnum 是一种静态枚举类, 通过自定义元类 `_StaticEnumMeta` 实现了增强的枚举项功能.

    功能特性:
    - 枚举项不可修改(保证静态性)
    - 对未赋值的整型声明(如 `X: int`), 会自动为其分配递增整数值(从 0 开始)
    - 支持枚举项添加属性(需启用 `enable_member_attribute`)
    - 支持类定义外部扩展枚举项属性(需启用 `enable_member_extension`)
    - 支持`遍历`、`keys()` / `values()` / `items()` 访问
    - 不对魔术属性、None 和布尔值进行类型转换, 因此它们不支持绑定额外属性
    - 嵌套类可自动转换为 StaticEnum 子枚举类


    参数说明 (由元类接收):
    - enable_member_attribute: bool
        是否启用为枚举项绑定属性的功能. 启用后, 可以通过 `MyEnum.A.some_attr = 123` 添加属性.
        同时, 枚举项会自动获得两个内置属性: `name` 和 `value`,
        其中 `name` 保存变量名(如 `'A'`), `value` 保存枚举项的值(如 `MyEnum.A` 的实际值

    - enable_member_extension: bool
        是否允许在类定义外部对枚举项添加新属性, 例如在运行时动态添加.

    提供的方法 Methods:
    - cls.members() -> list[(key, value)]
        获取所有枚举项组成的键值对列表

    - cls.items() -> dict_items
        返回所有枚举项的 (key, value) 可迭代视图

    - cls.keys() -> dict_keys
        返回所有枚举项的键集合

    - cls.values() -> dict_values
        返回所有枚举项的值集合

    - cls.getItemByValue(value) -> EnumMember
        根据值查找对应的枚举成员, 否则抛出 AttributeError

    用法示例 Example:
        class TestEnum(StaticEnum, enable_member_attribute=True, enable_member_extension=True):
            A = '#ff0000'
            A.color_name = 'Red'
            A.ansi_font = 31
            A.ansi_background = 41
            B: int
            C: int
            D = None

            class TestEnum2(StaticEnum, enable_member_attribute=True):
                AA = '#ff00ff'
                BB = 1
                CC = 2
                DD: int
                EE: int

            class TestEnum3(StaticEnum):
                AAA = '#00ff00'
                BBB: int

            class TestEnum4:
                AAAA = '#0000ff'
                BBBB: int

        TestEnum.A.color_name = 'Rot'               # success 成功
        TestEnum.A.font_family = 'Arial'            # success 成功
        TestEnum.TestEnum2.AA.color_name = 'Pink'   # failed 失败, not allowed 行为禁止
        TestEnum.TestEnum3.AAA.color_name = 'Green' # failed 失败, str has no attribute 'color_name' 字符串没有 color_name 属性
        TestEnum.TestEnum4.AAAA.color_name = 'Blue' # failed 失败, str has no attribute 'color_name' 字符串没有 color_name 属性
    """

    def __hasattr__(self, item):
        return item in self.__SE_members__['all_members'].keys()

    def __getattr__(self, item):
        return self.__SE_members__['all_members'][item]

    @classmethod
    def members(cls) -> list:
        temp = []
        for key, value in cls.__SE_members__['all_members'].items():
            temp.append((key, value))
        return temp

    @classmethod
    def items(cls):
        return cls.__SE_members__['all_members'].items()

    @classmethod
    def keys(cls):
        return cls.__SE_members__['all_members'].keys()

    @classmethod
    def values(cls):
        return cls.__SE_members__['all_members'].values()

    @classmethod
    def getItemByValue(cls, item, default=_null):
        for key, value in cls.__SE_members__['all_members'].items():
            if value == item:
                return value
        error_text = f'Item {item} not found in {cls.__name__}'
        if default is not _null:
            return default
        raise AttributeError(ansi_color_text(error_text, 33))

    @classmethod
    def to_json(cls):
        temp = {}
        target_dict = cls.__SE_members__['own_members']
        for key, item in target_dict.items():
            try:
                json.dumps(item)
            except:
                if isinstance(item, _StaticEnumMeta):
                    item = item.to_json()
                else:
                    continue
            temp[key] = item
        return temp


"""
if __name__ == '__main__':
    class TestEnum(StaticEnum, enable_member_attribute=True):
        A = '#ff0000'
        A.color_name = 'Red'
        A.ansi_font = 31
        A.ansi_background = 41
        B: int
        C: int
        D = None

        class TestEnum2(StaticEnum):
            a = 1
            b = 3
            AA = '#ff00ff'
            BB: int
            CC: int

        class TestEnum3:
            AAA = '#00ff00'
            BBB: int

    print(TestEnum.A)  # output: #ff0000
    print(TestEnum.A.name)  # output: A
    print(TestEnum.A.color_name)  # output: Red
    print(TestEnum.A.ansi_font)  # output: 31
    print(type(TestEnum.A))  # output: <class '__main__._SEString'>
    print(type(TestEnum.TestEnum2.AA))  # output: <class 'str'>
    print(isinstance(TestEnum.A, str))  # output: True
    print('#ff0000' in TestEnum)  # output: True
    print(TestEnum.B, TestEnum.C)  # output: 0 1
    print(TestEnum.TestEnum2.BB, TestEnum.TestEnum2.CC, TestEnum.TestEnum3.BBB)  # output: 0 2 0
"""
