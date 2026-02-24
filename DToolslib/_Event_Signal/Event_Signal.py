import sys
import threading
import weakref
import typing


class EventSignalInstance:
    """
    EventSignalInstance: A thread-safe event signal system.
    事件信号, 支持线程安全.

    Supports attribute protection, signal-slot connections, strong and weak reference.
    支持属性保护、信号与槽连接, 强引用、弱引用.

    - Args:
        - name (str): Signal name. 信号名称.
        - *types (type or tuple): Types of signal arguments. 信号参数的类型.

    - Methods:
        - connect(slot, weak:bool=False):
            Connect a slot (callable) to the signal. weak is True for weak reference.
            连接槽函数, weak为True表示弱引用.

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数.

        - emit(*args, **kwargs):
            Emit the signal with arguments.
            发射信号.

        - replace(old_slot, new_slot):
            Replace a connected slot with a new one.
            替换已连接的槽函数.

    - Operator Overloads:
        - `+=`: Same as connect(). 等同于 connect()
        - `-=`: Same as disconnect(). 等同于 disconnect()

    - Note:
        For attribute protection or class-level usage, use EventSignal.
        如需属性保护或类级使用, 请使用 EventSignal 类.
    """

    def __init__(self, name: str, *types, context=None) -> None:
        if ... in types:
            self.__types = ...
        elif all(isinstance(typ, (type, tuple, typing.TypeVar, str, typing.Any)) for typ in types):
            self.__types = types
        else:
            raise TypeError(f'Invalid type {types} for signal {name}')
        self.__name: str = name
        self.__context = context
        self.__slots: list = []
        self.__lock = threading.Lock()

    def __str__(self) -> str:
        return f'<EventSignalInstance(slots:{len(self.__slots)}) {self.__name} at 0x{id(self):016X}>'

    def __repr__(self) -> str:
        return f"{self.__str__()}\n    - slots: {self.__slots}"

    def __iadd__(self, slot) -> 'EventSignalInstance':
        self.connect(slot)
        return self

    def __isub__(self, slot) -> 'EventSignalInstance':
        self.disconnect(slot)
        return self

    @property
    def slot_count(self) -> int:
        with self.__lock:
            return len(self.__slots)

    def __check_type(self, arg, required_type, idx, path=None) -> None:
        if path is None:
            path = []
        full_path = path + [idx + 1]
        path_text = '-'.join(str(i) for i in full_path)

        if isinstance(required_type, typing.TypeVar) or required_type is typing.Any:
            return

        elif isinstance(required_type, str):
            if self.__context:
                resolved_type = self.__context.get(required_type)
                if resolved_type is not None and isinstance(arg, resolved_type):
                    return
                else:
                    req_name = getattr(resolved_type, '__name__', str(resolved_type))
                    actual_name = type(arg).__name__
                    raise TypeError(
                        f'EventSignal "{self.__name}" {path_text}th argument requires "{req_name}", got "{actual_name}"'
                    )
            else:
                return

        elif isinstance(required_type, tuple):
            if idx == 0:
                if not isinstance(arg, (tuple, list)):
                    raise TypeError(
                        f'EventSignal "{self.__name}" {path_text}th argument expects tuple/list, got {type(arg).__name__}'
                    )
                if len(arg) != len(required_type):
                    raise TypeError(
                        f'EventSignal "{self.__name}" {path_text}th argument expects length {len(required_type)}, got {len(arg)}'
                    )
                for sub_idx, sub_type in enumerate(required_type):
                    self.__check_type(arg[sub_idx], sub_type, sub_idx, path=full_path)
            else:
                if not isinstance(arg, required_type):
                    raise TypeError(
                        f'EventSignal "{self.__name}" {path_text}th argument expects {required_type}, got {type(arg).__name__}'
                    )
            return

        if not isinstance(arg, required_type):
            if type(arg).__name__ == required_type.__name__:
                return
            req_name = getattr(required_type, '__name__', str(required_type))
            actual_name = type(arg).__name__
            raise TypeError(
                f'EventSignal "{self.__name}" {path_text}th argument requires "{req_name}", got "{actual_name}" instead.'
            )

    def _wrap_slot(self, slot, weak: bool):
        if not weak:
            return slot
        try:
            return weakref.WeakMethod(slot)
        except TypeError:
            try:
                return weakref.ref(slot)
            except TypeError:
                return slot

    def _resolve_slot(self, ref):
        if isinstance(ref, weakref.ReferenceType):
            return ref()
        return ref

    @property
    def slot_counts(self) -> int:
        with self.__lock:
            return len(self.__slots)

    def connect(self, slot, weak: bool = False) -> 'EventSignalInstance':
        if hasattr(slot, 'emit'):
            slot = slot.emit
        if not callable(slot):
            raise ValueError(f"Slot must be callable, got {type(slot).__name__}")

        wrapped = self._wrap_slot(slot, weak)

        with self.__lock:
            for existing in self.__slots:
                resolved = self._resolve_slot(existing)
                if resolved is slot:
                    return self
            self.__slots.append(wrapped)
        return self

    def disconnect(self, slot) -> 'EventSignalInstance':
        if hasattr(slot, 'emit'):
            slot = slot.emit
        if not callable(slot):
            raise ValueError(f"Slot must be callable, got {type(slot).__name__}")

        with self.__lock:
            for i in range(len(self.__slots) - 1, -1, -1):
                resolved = self._resolve_slot(self.__slots[i])
                if resolved is None or resolved is slot:
                    self.__slots.pop(i)
        return self

    def disconnect_all(self) -> 'EventSignalInstance':
        with self.__lock:
            self.__slots.clear()
        return self

    def emit(self, *args, **kwargs) -> None:
        if self.__types != ...:
            required_types = self.__types
            if len(args) != len(required_types):
                plural = "s" if len(required_types) > 1 else ""
                raise TypeError(
                    f'EventSignal "{self.__name}" requires {len(required_types)} argument{plural}, but {len(args)} given.'
                )
            for idx, req_type in enumerate(required_types):
                self.__check_type(args[idx], req_type, idx)

        with self.__lock:
            slots = list(self.__slots)

        for slot_ref in slots:
            slot = self._resolve_slot(slot_ref)
            if slot is None:
                with self.__lock:
                    if slot_ref in self.__slots:
                        self.__slots.remove(slot_ref)
                continue
            try:
                slot(*args, **kwargs)
            except Exception as e:
                print(f"[{self.__name}] Slot error: {e}")


class EventSignalBoundInstance(EventSignalInstance):
    def __init__(self, types, owner, name, is_class_signal=False, context=None):
        super().__init__(name, *types, context=context)
        self.__owner_ref = weakref.ref(owner)
        self.__is_class_signal = is_class_signal

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.__owner_ref().__name__}"
            if self.__is_class_signal
            else f"{self.__owner_ref().__class__.__name__} object"
        )
        return f'<EventSignal(slots:{self.slot_count}) {self._EventSignalInstance__name} of {owner_repr}>'


class EventSignal:
    """
    EventSignal: Event signal with attribute protection.
    事件信号, 支持属性保护.

    - Args:
        - *types (type or tuple): Types of signal arguments. 信号参数的类型.
        - isClassSignal (bool):  Whether the signal is a class signal. 是否为类级信号.
            - True: Class signal, shared across instances. 类级信号, 多个实例共享.
            - False (default): Instance signal, bound to each instance. 实例信号, 绑定到实例.

    - Methods:
        - connect(slot, weak:bool=False):
            Connect a slot (callable) to the signal. weak is True for weak reference.
            连接槽函数, weak为True表示弱引用.

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数.

        - emit(*args, **kwargs):
            Emit the signal with arguments.
            发射信号.

        - replace(old_slot, new_slot):
            Replace a connected slot with a new one.
            替换已连接的槽函数.

    - Operator Overloads:
        - `+=`: Equivalent to connect(). 等同于 connect().
        - `-=`: Equivalent to disconnect(). 等同于 disconnect().

    - Note:
        Define in class body only. Supports instance-level and class-level signals
        depending on the 'signal_scope' argument.
        仅可在类体中定义. 通过参数 signal_scope 可定义为实例信号或类信号.
    """
    attrs = ('__class_signals__', '__signals__', '__weakref__')

    def __init__(self, *types, isClassSignal: bool = False):
        self.__types = types
        self.__is_class_signal = isClassSignal
        self.__name = ""

    def __set_name__(self, owner, name):
        self.__name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        module = sys.modules.get(owner.__module__)
        context = module.__dict__ if module else None

        if self.__is_class_signal:
            if not hasattr(owner, '__class_signals__'):
                owner.__class_signals__ = {}
            if self not in owner.__class_signals__:
                owner.__class_signals__[self] = EventSignalBoundInstance(
                    self.__types, owner, self.__name,
                    is_class_signal=True,
                    context=context
                )
            return owner.__class_signals__[self]
        else:
            if not hasattr(instance, '__signals__'):
                instance.__signals__ = {}
            if self not in instance.__signals__:
                instance.__signals__[self] = EventSignalBoundInstance(
                    self.__types, instance, self.__name,
                    is_class_signal=False,
                    context=context
                )
            return instance.__signals__[self]

    def __set__(self, instance, value):
        raise AttributeError("EventSignal is not mutable ^o^")
