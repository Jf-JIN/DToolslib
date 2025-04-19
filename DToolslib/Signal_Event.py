
import typing
import threading
import queue
import time


class _BoundSignal:
    __name__: str = 'EventSignal'
    __qualname__: str = 'EventSignal'

    def __init__(self, types, owner, name, isClassSignal=False, async_exec=False) -> None:
        if all([isinstance(typ, (type, tuple, typing.TypeVar)) for typ in types]):
            self.__types = types
        else:
            raise TypeError('types must be a tuple of types')
        self.__owner = owner
        self.__name = name
        self.__isClassSignal: bool = isClassSignal
        self.__async_exec: bool = async_exec
        self.__queue_slot = queue.Queue()
        self.__thread_lock = threading.Lock()
        self.__slots = []
        if self.__async_exec:
            self.__thread_async_thread = threading.Thread(target=self.__process_queue, name=f'EventSignal_AsyncThread_{self.__name}', daemon=True)
            self.__thread_async_thread.start()

    def __process_queue(self):
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

    def connect(self, slot: typing.Union['EventSignal', typing.Callable]) -> None:
        with self.__thread_lock:
            if callable(slot):
                if slot not in self.__slots:
                    self.__slots.append(slot)
            elif isinstance(slot, _BoundSignal):
                self.__slots.append(slot.emit)
            else:
                raise ValueError('Slot must be callable')

    def disconnect(self, slot: typing.Union['EventSignal', typing.Callable]) -> None:
        with self.__thread_lock:
            if callable(slot):
                if slot in self.__slots:
                    self.__slots.remove(slot)
            elif isinstance(slot, _BoundSignal):
                if slot.emit in self.__slots:
                    self.__slots.remove(slot.emit)
            else:
                raise ValueError('Slot must be callable')

    def emit(self, *args, blocking: bool = False, timeout: float | None = None, **kwargs) -> None:
        """ 
        The blocking and timeout options are only valid if the signal is executed in an asynchronous manner.
        """
        with self.__thread_lock:
            required_types = self.__types
            required_types_count = len(self.__types)
            args_count = len(args)
            if required_types_count != args_count:
                raise TypeError(f'EventSignal "{self.__name}" requires {required_types_count} argument{"s" if required_types_count>1 else ""}, but {args_count} given.')
            for arg, (idx, required_type) in zip(args, enumerate(required_types)):
                if isinstance(required_type, typing.TypeVar):
                    continue
                if not isinstance(arg, required_type):
                    required_name = required_type.__name__
                    actual_name = type(arg).__name__
                    raise TypeError(f'EventSignal "{self.__name} {idx+1}th argument requires "{required_name}", got "{actual_name}" instead.')
            slots = self.__slots
            done_events = []
            for slot in slots:
                if not self.__async_exec:
                    slot(*args, **kwargs)
                else:
                    done_event = threading.Event() if blocking else None
                    self.__queue_slot.put((slot, args, kwargs, done_event))
                    if done_event:
                        done_events.append(done_event)

            if blocking and self.__async_exec:
                start_time = time.time()
                for event in done_events:
                    event: threading.Event
                    remaining = None
                    if timeout is not None:
                        elapsed = time.time() - start_time
                        remaining = max(0, timeout - elapsed)
                    if not event.wait(timeout=remaining):
                        raise TimeoutError(f"EventSignal '{self.__name}' timed out")

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.__owner.__name__}"
            if self.__isClassSignal
            else f"{self.__owner.__class__.__name__} object"
        )
        return f'<Signal EventSignal(slots:{len(self.__slots)}) {self.__name} of {owner_repr} at 0x{id(self.__owner):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{str(self.__slots).replace('_BoundSignal', 'EventSignal')}\n"

    def __del__(self) -> None:
        self.__slots.clear()


class EventSignal:
    """ 
    事件信号, 属性保护和异步操作, 同时线程安全
    Event signal, attribute protection and asynchronous operations are supported, 
    and it is thread-safe.

    - Args:
        - *types(type, tuple): 信号参数类型, Signal parameter types.
        - signal_scope(str): 信号作用域, Signal scope.
            - `instance`(default): 实例信号, Instance signal. 
            - `class`: 类信号, Class signal.

    - Methods:
        - connect: 连接信号槽, Connect signal slot.
        - disconnect: 断开信号槽, Disconnect signal slot.
        - emit: 发射信号, Emit signal.
    """

    def __init__(self, *types: typing.Union[type, tuple], signal_scope: str = 'instance', async_exec: bool = False) -> None:
        self.__types = types
        self.__scope = signal_scope
        self.__async_exec = async_exec

    def __get__(self, instance, instance_type) -> _BoundSignal:
        if instance is None:
            return self
        else:
            if self.__scope == 'class':
                return self.__handle_class_signal(instance_type)
            else:
                return self.__handle_instance_signal(instance)

    def __set__(self, instance, value) -> None:
        raise AttributeError('EventSignal is read-only, cannot be set')

    def __set_name__(self, instance, name) -> None:
        self.__name = name

    def __handle_class_signal(self, instance_type) -> _BoundSignal:
        if not hasattr(instance_type, '__class_signals__'):
            instance_type.__class_signals__ = {}
        if self not in instance_type.__class_signals__:
            instance_type.__class_signals__[self] = _BoundSignal(
                self.__types,
                instance_type,
                self.__name,
                isClassSignal=True,
                async_exec=self.__async_exec
            )
        return instance_type.__class_signals__[self]

    def __handle_instance_signal(self, instance) -> _BoundSignal:
        if not hasattr(instance, '__signals__'):
            instance.__signals__ = {}
        if self not in instance.__signals__:
            instance.__signals__[self] = _BoundSignal(
                self.__types,
                instance,
                self.__name,
                isClassSignal=False,
                async_exec=self.__async_exec
            )
        return instance.__signals__[self]


"""
if __name__ == '__main__':
    class Test:
        signal_instance_a = EventSignal(str)  # Instance Signal
        signal_instance_b = EventSignal(str, int)  # Instance Signal
        signal_class = EventSignal(str, int, signal_scope='class')  # Class Signal
    a = Test()
    b = Test()
    b.signal_instance_a.connect(print)
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
