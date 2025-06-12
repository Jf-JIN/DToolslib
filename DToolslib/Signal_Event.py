
import typing
import threading
import queue
import time
import builtins
import sys
from DToolslib.Color_Text import *


class BoundSignal:
    """
    BoundSignal: A thread-safe, optionally asynchronous event signal system.
    事件信号系统，支持线程安全与可选的异步执行。

    Supports attribute protection, signal-slot connections, optional slot priorities,
    and safe asynchronous operations across threads.
    支持属性保护、信号与槽连接、可选的槽函数优先级，以及跨线程的安全异步操作。

    - Args:
        - name (str): Signal name. 信号名称。
        - *types (type or tuple): Types of signal arguments. 信号参数的类型。
        - async_exec (bool): Whether to emit signals asynchronously. 是否异步发射信号。
        - use_priority (bool): Whether to call slots in priority order. 是否按优先级调用槽函数。

    - Methods:
        - connect(slot, priority=None):
            Connect a slot (callable) to the signal. Optionally specify priority.
            连接槽函数，可选指定优先级。

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数。

        - emit(*args, blocking=False, timeout=None, **kwargs):
            Emit the signal with arguments. If async, can block with timeout.
            发射信号；若为异步发射，可设置阻塞和超时。

        - replace(old_slot, new_slot):
            Replace a connected slot with a new one.
            替换已连接的槽函数。

    - Operator Overloads:
        - `+=`: Same as connect(). 等同于 connect()
        - `-=`: Same as disconnect(). 等同于 disconnect()

    - Note:
        For attribute protection or class-level usage, use EventSignal.
        如需属性保护或类级使用，请使用 EventSignal 类。
    """

    def __init__(self, name, *types, async_exec=False, use_priority=False, context=None) -> None:
        if ... in types:
            self.__types = ...
        elif all([isinstance(typ, (type, tuple, typing.TypeVar, str, typing.Any)) for typ in types]):
            self.__types = types
        else:
            error_text = f'Invalid type {types} for signal {name}'
            raise TypeError(error_text)
        self.__name = name
        self.__async_exec: bool = True if async_exec else False
        self.__use_priority: bool = True if use_priority else False
        self.__context: None | dict = context
        self.__queue_slot = queue.Queue()
        self.__thread_lock = threading.Lock()
        self.__slots = []
        if self.__use_priority:
            self.__slots_without_priority = []
            self.__slots_with_priority = {}
            self.__len_slots_with_priority = 0
            self.__len_slots_without_priority = 0

        if self.__async_exec:
            self.__thread_async_thread = threading.Thread(target=self.__process_queue, name=f'EventSignal_AsyncThread_{self.__name}', daemon=True)
            self.__thread_async_thread.start()

    def __process_queue(self) -> None:
        while True:
            params: tuple = self.__queue_slot.get()
            slot: typing.Callable = params[0]
            args: tuple = params[1]
            kwargs: dict = params[2]
            done_event: threading.Event | None = params[3]
            try:
                slot(*args, **kwargs)
            except Exception as e:
                print(f"[{self.__name}] Slot error: {e}")
            finally:
                if done_event:
                    done_event.set()
                self.__queue_slot.task_done()

    def __key_rule_for_sort_slots(self, item: tuple):
        """
        该函数请务必在self.__thread_lock下使用, 以避免线程安全问题
        """
        k, v = item
        return k if k >= 0 else self.__len_slots_with_priority + self.__len_slots_without_priority + k

    def __priority_connect(self, slot: typing.Union['EventSignal', 'BoundSignal ', typing.Callable], priority: int) -> None:
        """
        该函数请务必在self.__thread_lock下使用, 以避免线程安全问题
        """
        if priority is None:
            self.__slots_without_priority.append(slot)
        else:
            if priority in self.__slots_with_priority:
                error_text = f"Priority {priority} already exists with slot {self.__slots_with_priority[priority]}"
                raise ValueError(error_text)
            self.__slots_with_priority[priority] = slot

        self.__len_slots_without_priority = len(self.__slots_without_priority)
        self.__len_slots_with_priority = len(self.__slots_with_priority)
        sorted_items: list = sorted(self.__slots_with_priority.items(), key=self.__key_rule_for_sort_slots)
        temp: dict = {}
        for k, v in sorted_items:
            if k >= 0:
                temp[k] = v
            else:
                temp[self.__len_slots_with_priority + self.__len_slots_without_priority + k] = v
        ls_idx = 0
        self.__slots.clear()
        for idx in range(self.__len_slots_with_priority + self.__len_slots_without_priority):
            if idx not in temp:
                slot = self.__slots_without_priority[ls_idx]
                ls_idx += 1
            else:
                slot = temp[idx]
            self.__slots.append(slot)

    def __priority_disconnect(self, slot: typing.Union['EventSignal', typing.Callable]) -> None:
        """
        该函数请务必在self.__thread_lock下使用, 以避免线程安全问题.

        该函数运行前提是 self.__slots中存在slot, 故无需检查
        """
        if slot in self.__slots_with_priority:
            for key, value in list(self.__slots_with_priority.items()):
                if value == slot:
                    del self.__slots_with_priority[key]
                    break
        elif slot in self.__slots_without_priority:
            self.__slots_without_priority.remove(slot)

    def __priority_disconnect_all(self) -> None:
        """
        该函数请务必在self.__thread_lock下使用, 以避免线程安全问题.

        该函数运行前提是 self.__slots中存在slot, 故无需检查
        """
        self.__slots_with_priority.clear()
        self.__slots_without_priority.clear()

    def __copy__(self) -> 'EventSignal':
        return BoundSignal(self.__name, self.__types, async_exec=self.__async_exec, use_priority=self.__use_priority, context=self.__context)

    def __deepcopy__(self, memo: typing.Dict) -> 'EventSignal':
        return BoundSignal(self.__name, self.__types, async_exec=self.__async_exec, use_priority=self.__use_priority, context=self.__context)

    def __str__(self) -> str:
        return f'<Signal BoundSignal(slots:{len(self.__slots)}) {self.__name} at 0x{id(self):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{str(self.__slots)}\n"

    def __del__(self) -> None:
        if hasattr(self, '__slots'):
            self.__slots.clear()

    def __iadd__(self, slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        self.connect(slot)
        return self

    def __isub__(self, slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        self.disconnect(slot)
        return self

    def __check_type(self, arg, required_type, idx, path=[]) -> None:
        """
        此处检查如果出现问题, 则直接抛出错误, 故不需要返回任何值
        """
        if path is None:
            path = []
        full_path = path + [idx+1]
        path_text = '-'.join(str(i) for i in full_path)

        if isinstance(required_type, typing.TypeVar) or required_type == typing.Any:
            return

        # 支持字符串形式的类名（'AClass'）
        elif isinstance(required_type, str):
            if self.__context:
                required_type = self.__context.get(required_type, None)
                if required_type is not None and isinstance(arg, required_type):
                    return
                else:
                    required_name = getattr(required_type, '__name__', str(required_type))
                    actual_name = type(arg).__name__
                    error_text = f'EventSignal "{self.__name}" {path_text}th argument requires "{required_name}", got "{actual_name}"'
                    raise TypeError(error_text)
            else:
                error_text = f'EventSignal "{self.__name}" is missing a context parameter. String types({path_text}th argument "{required_type}") will not be parsed automatically. Please verify the argument types manually.'
                print(ansi_color_text(error_text, 33))
                return

        elif isinstance(required_type, tuple):
            if not isinstance(arg, (tuple, list)):
                error_text = f'EventSignal "{self.__name}" {path_text}th argument expects tuple/list, got {type(arg).__name__}'
                raise TypeError(error_text)
            if len(arg) != len(required_type):
                error_text = f'EventSignal "{self.__name}" {path_text}th  argument expects tuple/list of length {len(required_type)}, got {len(arg)}'
                raise TypeError(error_text)
            for sub_idx, sub_type in enumerate(required_type):
                self.__check_type(arg[sub_idx], sub_type, sub_idx, path=full_path)
            return

        if not isinstance(arg, required_type):
            if type(arg).__name__ == required_type.__name__:
                return
            print(arg, required_type, isinstance(arg, required_type), type(arg) == required_type, type(arg), type(required_type))
            required_name = getattr(required_type, '__name__', str(required_type))
            actual_name = type(arg).__name__
            error_text = f'EventSignal "{self.__name}" {path_text}th argument requires "{required_name}", got "{actual_name}" instead.'
            raise TypeError(error_text)

    @property
    def slot_counts(self) -> int:
        with self.__thread_lock:
            return len(self.__slots)

    def connect(self, slot: typing.Union['EventSignal', typing.Callable], priority: int = None) -> typing.Self:
        with self.__thread_lock:
            if not isinstance(priority, (int, type(None))):
                error_text = f'priority must be int, not {type(priority).__name__}'
                raise TypeError(error_text)
            if isinstance(slot, (_BoundSignal, BoundSignal)):
                slot = slot.emit

            if callable(slot):
                if slot not in self.__slots:
                    if not self.__use_priority:
                        self.__slots.append(slot)
                    else:
                        self.__priority_connect(slot, priority)
            else:
                error_text = f'Slot must be callable'
                raise ValueError(error_text)
            return self

    def disconnect(self, slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        with self.__thread_lock:
            if isinstance(slot, (_BoundSignal, BoundSignal)):
                slot = slot.emit
            if callable(slot):
                if slot in self.__slots:
                    self.__slots.remove(slot)
                    if self.__use_priority:
                        self.__priority_disconnect(slot)
            else:
                error_text = 'Slot must be callable'
                raise ValueError(error_text)
            return self

    def disconnect_all(self) -> typing.Self:
        with self.__thread_lock:
            self.__slots.clear()
            if self.__use_priority:
                self.__priority_disconnect_all()
            return self

    def replace(self, old_slot: typing.Union['EventSignal', typing.Callable], new_slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        with self.__thread_lock:
            if not callable(new_slot):
                error_text = 'New slot must be callable'
                raise ValueError(error_text)
            if old_slot not in self.__slots:
                error_text = 'Old slot not found'
                raise ValueError(error_text)
            if new_slot in self.__slots:
                error_text = 'New slot already exists'
                raise ValueError(error_text)
            idx_slots_old: int = self.__slots.index(old_slot)
            self.__slots[idx_slots_old] = new_slot
            if self.__use_priority:
                if old_slot in self.__slots_with_priority:
                    for k, v in self.__slots_with_priority.items():
                        if v == old_slot:
                            self.__slots_with_priority[k] = new_slot
                            break
                elif old_slot in self.__slots_without_priority:
                    idx_ls_old: int = self.__slots_without_priority.index(old_slot)
                    self.__slots_without_priority[idx_ls_old] = new_slot
            return self

    def emit(self, *args, blocking: bool = False, timeout: float | int | None = None, **kwargs) -> None:
        """
        The blocking and timeout options are only valid if the signal is executed in an asynchronous manner.
        """
        if not isinstance(blocking, bool):
            error_text = 'Blocking must be a boolean'
            raise TypeError(error_text)
        if not isinstance(timeout, (float, int, type(None))):
            error_text = 'Timeout must be a float or int or None'
            raise TypeError(error_text)
        with self.__thread_lock:
            if self.__types != ...:
                required_types = self.__types
                required_types_count = len(self.__types)
                args_count = len(args)
                if required_types_count != args_count:
                    error_text = f'EventSignal "{self.__name}" requires {required_types_count} argument{"s" if required_types_count>1 else ""}, but {args_count} given.'
                    raise TypeError(error_text)
                for arg, (idx, required_type) in zip(args, enumerate(required_types)):
                    self.__check_type(arg, required_type, idx)
            slots = self.__slots
            done_events = []
            for slot in slots:
                if not self.__async_exec:
                    try:
                        slot(*args, **kwargs)
                    except Exception as e:
                        raise e
                else:
                    done_event = threading.Event() if blocking else None
                    self.__queue_slot.put((slot, args, kwargs, done_event))
                    if done_event:
                        done_events.append(done_event)
            # 阻塞超时检查
            if blocking and self.__async_exec:
                start_time = time.time()
                for event in done_events:
                    event: threading.Event
                    remaining = None
                    if timeout is not None:
                        elapsed = time.time() - start_time
                        remaining = max(0, timeout - elapsed)
                    if not event.wait(timeout=remaining):
                        error_text = f"Signal '{self.__name}' timed out"
                        raise TimeoutError(error_text)


class _BoundSignal(BoundSignal):
    __name__: str = 'EventSignal'
    __qualname__: str = 'EventSignal'

    def __init__(self, types, owner, name, isClassSignal=False, async_exec=False, use_priority=False, context=None) -> None:
        super().__init__(name, *types, async_exec=async_exec, use_priority=use_priority, context=context)
        self.__owner = owner
        self.__isClassSignal = isClassSignal

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.__owner.__name__}"
            if self.__isClassSignal
            else f"{self.__owner.__class__.__name__} object"
        )
        return f'<Signal EventSignal(slots:{len(self.__slots)}) {self.__name} of {owner_repr} at 0x{id(self.__owner):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{str(self.__slots).replace('_BoundSignal', 'EventSignal')}\n"


class EventSignal:
    """
    EventSignal: Event signal with attribute protection, asynchronous operation, and thread safety.
    事件信号，支持属性保护、异步操作，同时线程安全。

    - Args:
        - *types (type or tuple): Types of signal arguments. 信号参数的类型。
        - signal_scope (str): Scope of the signal: "instance" or "class". 信号作用域，可选 "instance" 或 "class"。
            - "instance" (default): Signal bound to each instance. 默认，绑定到实例的信号。
            - "class": Signal shared across the class. 类级信号，多个实例共享。
        - async_exec (bool): Whether to emit signals asynchronously. 是否异步发射信号。
        - use_priority (bool): Whether to call slots in priority order. 是否按优先级调用槽函数。

    - Methods:
        - connect(slot, priority=None):
            Connect a slot (callable) to the signal. Optionally specify priority.
            连接槽函数，可选指定优先级。

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数。

        - emit(*args, blocking=False, timeout=None, **kwargs):
            Emit the signal with arguments. If async, can block with timeout.
            发射信号；若为异步发射，可设置阻塞和超时。

        - replace(old_slot, new_slot):
            Replace a connected slot with a new one.
            替换已连接的槽函数。

    - Operator Overloads:
        - `+=`: Equivalent to connect(). 等同于 connect()。
        - `-=`: Equivalent to disconnect(). 等同于 disconnect()。

    - Note:
        Define in class body only. Supports instance-level and class-level signals
        depending on the 'signal_scope' argument.
        仅可在类体中定义。通过参数 signal_scope 可定义为实例信号或类信号。
    """

    def __init__(self, *types: typing.Union[type, tuple], signal_scope: str = 'instance', async_exec: bool = False) -> None:
        self.__types = types
        self.__scope = signal_scope
        self.__async_exec: bool = async_exec

    def __get__(self, instance, instance_type) -> _BoundSignal:
        if instance is None:
            return self
        else:
            module = sys.modules[instance_type.__module__]
            module_globals = module.__dict__
            if self.__scope == 'class':
                return self.__handle_class_signal(instance_type, module_globals)
            else:
                return self.__handle_instance_signal(instance, module_globals)

    def __set__(self, instance, value) -> None:
        if value is self.__get__(instance, type(instance)):
            return
        error_text = f'EventSignal is read-only, cannot be set'
        raise AttributeError(error_text)

    def __set_name__(self, instance, name) -> None:
        self.__name = name

    def __handle_class_signal(self, instance_type, context) -> _BoundSignal:
        if not hasattr(instance_type, '__class_signals__'):
            instance_type.__class_signals__ = {}
        if self not in instance_type.__class_signals__:
            instance_type.__class_signals__[self] = _BoundSignal(
                self.__types,
                instance_type,
                self.__name,
                isClassSignal=True,
                async_exec=self.__async_exec,
                context=context,
            )
        return instance_type.__class_signals__[self]

    def __handle_instance_signal(self, instance, context) -> _BoundSignal:
        if not hasattr(instance, '__signals__'):
            instance.__signals__ = {}
        if self not in instance.__signals__:
            instance.__signals__[self] = _BoundSignal(
                self.__types,
                instance,
                self.__name,
                isClassSignal=False,
                async_exec=self.__async_exec,
                context=context,
            )
        return instance.__signals__[self]


"""
if __name__ == '__main__':
    class Test:
        signal_instance_a = EventSignal(str)                        # Instance Signal
        signal_instance_b = EventSignal(str, int)                   # Instance Signal
        signal_class = EventSignal(str, int, signal_scope='class')  # Class Signal
    a = Test()
    b = Test()
    b.signal_instance_a += print
    a.signal_instance_b.connect(b.signal_instance_a)
    b.signal_instance_a.emit('This is a test message')
    a.signal_instance_a.disconnect(b.signal_instance_a)

    # output: This is a test message
    print(a.signal_class is b.signal_class)  # output: True
    print(a.signal_instance_a is b.signal_instance_a)  # output: False
    print(type(a.signal_class))  # output: <class '__main__.EventSignal'>
    print(a.__signals__)  # output: {...} a dict with 2 keys, the values are signal instances. You can also see the slots of the signal.
    print(a.__class_signals__)  # output: {...} a dict with 1 keys, the values are signal instances. You can also see the slots of the signal.
"""
