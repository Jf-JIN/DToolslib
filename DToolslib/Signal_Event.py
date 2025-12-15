import queue
import sys
import threading
import time
import weakref

from DToolslib.Color_Text import *


class BoundSignal:
    """
    BoundSignal: A thread-safe, optionally asynchronous event signal system.
    事件信号系统, 支持线程安全与可选的异步执行.

    Supports attribute protection, signal-slot connections, optional slot priorities,
    and safe asynchronous operations across threads.
    支持属性保护、信号与槽连接、可选的槽函数优先级, 以及跨线程的安全异步操作.

    - Args:
        - name (str): Signal name. 信号名称.
        - *types (type or tuple): Types of signal arguments. 信号参数的类型.
        - async_exec (bool): Whether to emit signals asynchronously. 是否异步发射信号.
        - use_priority (bool): Whether to call slots in priority order. 是否按优先级调用槽函数.

    - Methods:
        - connect(slot, priority=None):
            Connect a slot (callable) to the signal. Optionally specify priority.
            连接槽函数, 可选指定优先级.

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数.

        - emit(*args, blocking=False, timeout=None, **kwargs):
            Emit the signal with arguments. If async, can block with timeout.
            发射信号; 若为异步发射, 可设置阻塞和超时.

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
        self.__stop_event = threading.Event()
        self.__thread_lock = threading.Lock()
        self.__slots = []
        if self.__use_priority:
            self.__slots_without_priority = []
            self.__slots_with_priority = {}
            self.__len_slots_with_priority = 0
            self.__len_slots_without_priority = 0

        if self.__async_exec:
            self.__thread_async_thread = threading.Thread(target=self.__process_queue,
                                                          name=f'EventSignal_AsyncThread_{self.__name}', daemon=True)
            self.__thread_async_thread.start()

    def __process_queue(self) -> None:
        while not self.__stop_event.is_set():
            params = self.__queue_slot.get()
            if params is None:
                self.__queue_slot.task_done()
                continue
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

    def __priority_connect(self, slot: typing.Union['EventSignal', 'BoundSignal ', typing.Callable],
                           priority: int) -> None:
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
        for key, value in list(self.__slots_with_priority.items()):
            if value is slot:
                del self.__slots_with_priority[key]
                break
        if slot in self.__slots_without_priority:
            self.__slots_without_priority.remove(slot)

    def __priority_disconnect_all(self) -> None:
        """
        该函数请务必在self.__thread_lock下使用, 以避免线程安全问题.

        该函数运行前提是 self.__slots中存在slot, 故无需检查
        """
        self.__slots_with_priority.clear()
        self.__slots_without_priority.clear()

    def __copy__(self):
        return BoundSignal(self.__name, *self.__types,
                           async_exec=self.__async_exec,
                           use_priority=self.__use_priority,
                           context=self.__context)

    def __deepcopy__(self, memo):
        return self.__copy__()

    def __str__(self) -> str:
        return f'<Signal BoundSignal(slots:{len(self.__slots)}) {self.__name} at 0x{id(self):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{str(self.__slots)}\n"

    def __del__(self):
        try:
            self.cleanup()
        except:
            pass

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
        full_path = path + [idx + 1]
        path_text = '-'.join(str(i) for i in full_path)

        if isinstance(required_type, typing.TypeVar) or required_type == typing.Any:
            return

        # 支持字符串形式的类名('AClass')
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
                return

        elif isinstance(required_type, tuple):
            if idx == 0:
                if not isinstance(arg, (tuple, list)):
                    error_text = f'EventSignal "{self.__name}" {path_text}th argument expects tuple/list, got {type(arg).__name__}'
                    raise TypeError(error_text)
                if len(arg) != len(required_type):
                    error_text = f'EventSignal "{self.__name}" {path_text}th  argument expects tuple/list of length {len(required_type)}, got {len(arg)}'
                    raise TypeError(error_text)
                for sub_idx, sub_type in enumerate(required_type):
                    self.__check_type(arg[sub_idx], sub_type, sub_idx, path=full_path)
            else:
                if not isinstance(arg, required_type):
                    error_text = f'EventSignal "{self.__name}" {path_text}th argument expects {required_type}, got {type(arg).__name__}'
                    raise TypeError(error_text)
            return

        if not isinstance(arg, required_type):
            if type(arg).__name__ == required_type.__name__:
                return
            # print(arg, required_type, isinstance(arg, required_type), type(arg) == required_type, type(arg),
            # type(required_type))
            required_name = getattr(required_type, '__name__', str(required_type))
            actual_name = type(arg).__name__
            error_text = f'EventSignal "{self.__name}" {path_text}th argument requires "{required_name}", got "{actual_name}" instead.'
            raise TypeError(error_text)

    @staticmethod
    def __wrap_slot(slot):
        try:
            return weakref.WeakMethod(slot)  # 绑定方法
        except TypeError:
            try:
                return weakref.ref(slot)  # 普通函数/可调用
            except TypeError:
                return slot  # 退回强引用

    @staticmethod
    def __resolve_slot(ref):
        if isinstance(ref, weakref.ReferenceType):
            return ref()  # 失效则返回 None
        return ref

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
            if not callable(slot):
                error_text = f'Slot must be callable'
                raise ValueError(error_text)

            slot_ref = self.__wrap_slot(slot)
            # 避免重复：对强引用可直接 in，对弱引用需要根据解引用比较
            for existing in self.__slots:
                ex = self.__resolve_slot(existing)
                if ex is slot:
                    return self  # 已存在

            if not self.__use_priority:
                self.__slots.append(slot_ref)
            else:
                self.__priority_connect(slot_ref, priority)
            return self

    def disconnect(self, slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        with self.__thread_lock:
            from_types = (BoundSignal,)
            if isinstance(slot, from_types):
                slot = slot.emit
            if not callable(slot):
                error_text = 'Slot must be callable'
                raise ValueError(error_text)

            # 主表删除（按解引用匹配）
            for i in range(len(self.__slots) - 1, -1, -1):
                ex = self.__resolve_slot(self.__slots[i])
                if ex is None or ex is slot:
                    victim = self.__slots.pop(i)
                    if self.__use_priority:
                        self.__priority_disconnect(victim)
            return self

    def disconnect_all(self) -> typing.Self:
        with self.__thread_lock:
            self.__slots.clear()
            if self.__use_priority:
                self.__priority_disconnect_all()
            return self

    def replace(self, old_slot: typing.Union['EventSignal', typing.Callable],
                new_slot: typing.Union['EventSignal', typing.Callable]) -> typing.Self:
        with self.__thread_lock:
            if not callable(new_slot):
                raise ValueError('New slot must be callable')
            # 找 old_slot
            idx = -1
            for i, ref in enumerate(self.__slots):
                ex = self.__resolve_slot(ref)
                if ex is old_slot:
                    idx = i
                    break
            if idx == -1:
                raise ValueError('Old slot not found')

            # 检查重复
            for ref in self.__slots:
                ex = self.__resolve_slot(ref)
                if ex is new_slot:
                    raise ValueError('New slot already exists')

            new_ref = self.__wrap_slot(new_slot)
            old_ref = self.__slots[idx]
            self.__slots[idx] = new_ref

            if self.__use_priority:
                # 同步子结构
                for k, v in list(self.__slots_with_priority.items()):
                    if v is old_ref:
                        self.__slots_with_priority[k] = new_ref
                        break
                for j, v in enumerate(list(self.__slots_without_priority)):
                    if v is old_ref:
                        self.__slots_without_priority[j] = new_ref
                        break
            return self

    def emit(self, *args, blocking: bool = False, timeout: float | int | None = None, **kwargs) -> None:
        """
        The blocking and timeout options are only valid if the signal is executed in an asynchronous manner.
        """
        if not isinstance(blocking, bool):
            raise TypeError('Blocking must be a boolean')
        if not isinstance(timeout, (float, int, type(None))):
            raise TypeError('Timeout must be a float or int or None')

        with self.__thread_lock:
            # 类型检查
            if self.__types != ...:
                required_types = self.__types
                if len(required_types) != len(args):
                    raise TypeError(
                        f'EventSignal "{self.__name}" requires {len(required_types)} argument'
                        f'{"s" if len(required_types) > 1 else ""}, but {len(args)} given.'
                    )
                for idx, required_type in enumerate(required_types):
                    self.__check_type(args[idx], required_type, idx)

            # 发射
            done_events = []
            # 复制当前快照，避免迭代过程中被修改
            slots_snapshot = list(self.__slots)

            # 发射在锁外执行，降低锁持有时间
        for slot_ref in slots_snapshot:
            slot = self.__resolve_slot(slot_ref)
            if slot is None:
                # 弱引用已失效：惰性清理
                with self.__thread_lock:
                    if slot_ref in self.__slots:
                        self.__slots.remove(slot_ref)
                continue

            if not self.__async_exec:
                slot(*args, **kwargs)
            else:
                done_event = threading.Event() if blocking else None
                self.__queue_slot.put((slot_ref, args, kwargs, done_event))
                if done_event:
                    done_events.append(done_event)

        if blocking and self.__async_exec:
            start_time = time.time()
            for ev in done_events:
                remaining = None
                if timeout is not None:
                    elapsed = time.time() - start_time
                    remaining = max(0, timeout - elapsed)
                if not ev.wait(timeout=remaining):
                    raise TimeoutError(f"Signal '{self.__name}' timed out")

    def close(self, join_timeout: float | None = None):
        if getattr(self, "_BoundSignal__async_exec", False) and hasattr(self, "_BoundSignal__thread_async_thread"):
            if not self.__stop_event.is_set():
                self.__stop_event.set()
                try:
                    self.__queue_slot.put(None)
                except Exception:
                    pass
                try:
                    self.__thread_async_thread.join(join_timeout or 0)
                except Exception:
                    pass

    def cleanup(self):
        """彻底清理资源"""
        self.disconnect_all()
        if hasattr(self, '_BoundSignal__async_exec') and self.__async_exec:
            self.close(join_timeout=5.0)

        # 清理对owner的引用
        if hasattr(self, '_BoundSignal__owner_ref'):
            self.__owner_ref = None


class _BoundSignal(BoundSignal):
    __name__: str = 'EventSignal'
    __qualname__: str = 'EventSignal'

    def __init__(self, types, owner, name, isClassSignal=False, async_exec=False, use_priority=False,
                 context=None) -> None:
        super().__init__(name, *types, async_exec=async_exec, use_priority=use_priority, context=context)
        self.__owner_ref = weakref.ref(owner)
        self.__isClassSignal = isClassSignal

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.self.__owner_ref().__name__}"
            if self.__isClassSignal
            else f"{self.self.__owner_ref().__class__.__name__} object"
        )
        return f'<Signal EventSignal(slots:{len(self.__slots)}) {self.__name} of {owner_repr} at 0x{id(self.self.__owner_ref()):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{str(self.__slots).replace('_BoundSignal', 'EventSignal')}\n"


class EventSignal:
    """
    EventSignal: Event signal with attribute protection, asynchronous operation, and thread safety.
    事件信号, 支持属性保护、异步操作, 同时线程安全.

    - Args:
        - *types (type or tuple): Types of signal arguments. 信号参数的类型.
        - isClassSignal (bool):  Whether the signal is a class signal. 是否为类级信号.
            - True: Class signal, shared across instances. 类级信号, 多个实例共享.
            - False (default): Instance signal, bound to each instance. 实例信号, 绑定到实例.
        - async_exec (bool): Whether to emit signals asynchronously. 是否异步发射信号.
        - use_priority (bool): Whether to call slots in priority order. 是否按优先级调用槽函数.

    - Methods:
        - connect(slot, priority=None):
            Connect a slot (callable) to the signal. Optionally specify priority.
            连接槽函数, 可选指定优先级.

        - disconnect(slot):
            Disconnect a slot from the signal.
            断开已连接的槽函数.

        - emit(*args, blocking=False, timeout=None, **kwargs):
            Emit the signal with arguments. If async, can block with timeout.
            发射信号; 若为异步发射, 可设置阻塞和超时.

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
    attrs = ['__signals__', '__weakref__']

    def __init__(self, *types: typing.Union[type, str, tuple], isClassSignal: bool = False,
                 async_exec: bool = False) -> None:
        self.__types = types
        self.__isClassSignal = isClassSignal
        self.__async_exec: bool = async_exec

    def __get__(self, instance, instance_type) -> _BoundSignal:
        if instance is None:
            return self
        else:
            module = sys.modules[instance_type.__module__]
            module_globals = module.__dict__
            if self.__isClassSignal:
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
            try:
                instance_type.__class_signals__ = {}
            except Exception as e:
                error_text = f'{type(instance_type).__name__}: Cannot create attribute "__signals__". Error: {e}'
                error_text = ansi_color_text(error_text, 33)
                raise AttributeError(error_text)
        if self not in instance_type.__class_signals__:
            __bound_signal = _BoundSignal(
                self.__types,
                instance_type,
                self.__name,
                isClassSignal=True,
                async_exec=self.__async_exec,
                context=context,
            )
            try:
                instance_type.__class_signals__[self] = __bound_signal
            except Exception as e:
                error_text = f'{type(instance_type).__name__}: Cannot assign signal "{self.__name}" to "__signals__". Error: {e}'
                error_text = ansi_color_text(error_text, 33)
                raise AttributeError(error_text)
        return instance_type.__class_signals__[self]

    def __handle_instance_signal(self, instance, context) -> _BoundSignal:
        if not hasattr(instance, '__signals__'):
            try:
                instance.__signals__ = weakref.WeakKeyDictionary()
            except Exception as e:
                error_text = f'{type(instance).__name__}: Cannot create attribute "__signals__". Error: {e}'
                error_text = ansi_color_text(error_text, 33)
                raise AttributeError(error_text)
        if self not in instance.__signals__:
            __bound_signal = _BoundSignal(
                self.__types,
                instance,
                self.__name,
                isClassSignal=False,
                async_exec=self.__async_exec,
                context=context,
            )
            try:
                instance.__signals__[self] = __bound_signal
            except Exception as e:
                error_text = f'{type(instance).__name__}: Cannot assign signal "{self.__name}" to "__signals__". Error: {e}'
                error_text = ansi_color_text(error_text, 33)
                raise AttributeError(error_text)
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

if __name__ == '__main__':
    import gc

    def test_memory_leak():
        """测试EventSignal内存泄漏"""

        class TestClass:
            signal = EventSignal(str, async_exec=True)

        # 创建测试实例
        def create_test_instance():
            obj = TestClass()
            obj.signal.connect(lambda x: print(x))
            return weakref.ref(obj)

        def test():
            if weak_ref() is not None:
                print(f"第{i + 1}次测试：内存泄漏！实例未被释放")

            # 检查BoundSignal实例
            bound_signals = [obj for obj in gc.get_objects()
                             if hasattr(obj, '__class__') and 'BoundSignal' in obj.__class__.__name__]
            print(f"存活BoundSignal数量: {len(bound_signals)}")

        # 多次测试
        for i in range(100):
            weak_ref = create_test_instance()
            gc.collect()  # 强制垃圾回收
            test()

    test_memory_leak()
