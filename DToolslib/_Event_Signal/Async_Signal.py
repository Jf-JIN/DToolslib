import sys
import threading
import weakref
import typing
from typing import Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, Future
import atexit


class _GlobalExecutor:
    def __init__(self):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()

    def get(self) -> ThreadPoolExecutor:
        with self._lock:
            if self._executor is None or self._executor._shutdown:
                self._executor = ThreadPoolExecutor(max_workers=32, thread_name_prefix="SignalWorker")
                atexit.register(self._shutdown)
            return self._executor

    def _shutdown(self):
        if self._executor and not self._executor._shutdown:
            self._executor.shutdown(wait=False)


_GLOBAL_EXECUTOR = _GlobalExecutor()


class AsyncSignalInstance:
    def __init__(self, name: str, *types, use_priority: bool = False, context: Optional[dict] = None) -> None:
        if ... in types:
            self.__types = ...
        elif all(isinstance(t, (type, tuple, typing.TypeVar, str, type(Any))) for t in types):
            self.__types = types
        else:
            raise TypeError(f'Invalid type {types} for signal {name}')
        self.__name = name
        self.__use_priority = bool(use_priority)
        self.__context = context
        self.__slots: list[tuple[int, object]] = []  # (priority, slot_ref)
        self.__lock = threading.Lock()

    def __str__(self) -> str:
        return f'<AsyncSignalInstance(slots:{len(self.__slots)}) {self.__name} at 0x{id(self):016X}>'

    def __repr__(self) -> str:
        return f"{self.__str__()}\n    - slots (priority, ref): {[(p, type(r).__name__) for p, r in self.__slots]}"

    def __iadd__(self, slot) -> 'AsyncSignalInstance':
        self.connect(slot)
        return self

    def __isub__(self, slot) -> 'AsyncSignalInstance':
        self.disconnect(slot)
        return self

    @property
    def slot_count(self) -> int:
        with self.__lock:
            return len(self.__slots)

    def __check_type(self, arg, required_type, idx: int, path=None) -> None:
        if path is None:
            path = []
        full_path = path + [idx + 1]
        path_text = '-'.join(str(i) for i in full_path)

        if isinstance(required_type, typing.TypeVar) or required_type is Any:
            return
        elif isinstance(required_type, str):
            if self.__context:
                resolved = self.__context.get(required_type)
                if resolved is not None and isinstance(arg, resolved):
                    return
                req_name = getattr(resolved, '__name__', str(resolved))
                actual_name = type(arg).__name__
                raise TypeError(
                    f'EventSignal "{self.__name}" {path_text}th argument requires "{req_name}", got "{actual_name}"'
                )
            else:
                return
        elif isinstance(required_type, tuple):
            if not isinstance(arg, (tuple, list)):
                raise TypeError(
                    f'EventSignal "{self.__name}" {path_text}th argument expects tuple/list, got {type(arg).__name__}')
            if len(arg) != len(required_type):
                raise TypeError(
                    f'EventSignal "{self.__name}" {path_text}th argument length mismatch: expected {len(required_type)}, got {len(arg)}')
            for sub_idx, sub_type in enumerate(required_type):
                self.__check_type(arg[sub_idx], sub_type, sub_idx, path=full_path)
            return
        else:
            if not isinstance(arg, required_type):
                if type(arg).__name__ == required_type.__name__:
                    return
                req_name = getattr(required_type, '__name__', str(required_type))
                actual_name = type(arg).__name__
                raise TypeError(
                    f'EventSignal "{self.__name}" {path_text}th argument requires "{req_name}", got "{actual_name}" instead.'
                )

    @staticmethod
    def _wrap_slot(slot: Callable, weak: bool):
        if not weak:
            return slot
        try:
            return weakref.WeakMethod(slot)
        except TypeError:
            try:
                return weakref.ref(slot)
            except TypeError:
                return slot

    @staticmethod
    def _resolve_slot(ref):
        if isinstance(ref, weakref.ReferenceType):
            return ref()
        return ref

    @property
    def slot_counts(self) -> int:
        with self.__lock:
            return len(self.__slots)

    def connect(self, slot, priority: Optional[int] = None, weak: bool = False) -> 'AsyncSignalInstance':
        if hasattr(slot, 'emit'):
            slot = slot.emit
        if not callable(slot):
            raise ValueError(f"Slot must be callable, got {type(slot).__name__}")

        if priority is None:
            priority = 0
        elif not self.__use_priority:
            raise ValueError("Priority not enabled for this signal (use_priority=False)")

        wrapped = self._wrap_slot(slot, weak)

        with self.__lock:
            for p, ref in self.__slots:
                if self._resolve_slot(ref) is slot:
                    return self
            self.__slots.append((priority, wrapped))

        return self

    def disconnect(self, slot) -> 'AsyncSignalInstance':
        if hasattr(slot, 'emit'):
            slot = slot.emit
        if not callable(slot):
            raise ValueError(f"Slot must be callable, got {type(slot).__name__}")

        with self.__lock:
            for i in range(len(self.__slots) - 1, -1, -1):
                p, ref = self.__slots[i]
                if self._resolve_slot(ref) is slot:
                    del self.__slots[i]

        return self

    def disconnect_all(self) -> 'AsyncSignalInstance':
        with self.__lock:
            self.__slots.clear()
        return self

    def emit_sync(self, *args, **kwargs) -> None:
        self._emit_impl(*args, **kwargs)

    def emit(self, *args, sync: bool = False, **kwargs) -> Optional[list]:
        """
        默认异步发射。
        - sync=True: 同步执行（等价于 emit_sync）
        - 返回 Future 列表（仅异步时）
        """
        if sync:
            self._emit_impl(*args, **kwargs)
            return None
        else:
            with self.__lock:
                slots_snapshot = sorted(self.__slots, key=lambda x: x[0])

            futures = []
            executor = _GLOBAL_EXECUTOR.get()
            for priority, slot_ref in slots_snapshot:
                slot = self._resolve_slot(slot_ref)
                if slot is None:
                    continue
                future = executor.submit(self._call_slot_safe, slot, args, kwargs)
                futures.append(future)
            return futures

    def _emit_impl(self, *args, **kwargs) -> None:
        if self.__types != ...:
            if len(args) != len(self.__types):
                plural = "s" if len(self.__types) != 1 else ""
                raise TypeError(
                    f'EventSignal "{self.__name}" requires {len(self.__types)} argument{plural}, got {len(args)}')
            for idx, typ in enumerate(self.__types):
                self.__check_type(args[idx], typ, idx)

        with self.__lock:
            slots_snapshot = sorted(self.__slots, key=lambda x: x[0])

        for priority, slot_ref in slots_snapshot:
            slot = self._resolve_slot(slot_ref)
            if slot is None:
                continue
            self._call_slot_safe(slot, args, kwargs)

    def _call_slot_safe(self, slot, args, kwargs):
        try:
            slot(*args, **kwargs)
        except Exception as e:
            print(f"[{self.__name}] Slot error in {slot}: {e}", file=sys.stderr)


class AsyncSignalBoundInstance(AsyncSignalInstance):
    def __init__(self, types, owner, name, is_class_signal=False, use_priority=False, context=None):
        super().__init__(name, *types, use_priority=use_priority, context=context)
        self.__owner_ref = weakref.ref(owner)
        self.__is_class_signal = is_class_signal

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.__owner_ref().__name__}"
            if self.__is_class_signal
            else f"{self.__owner_ref().__class__.__name__} object"
        )
        return f'<AsyncSignal(slots:{self.slot_count}) {self._AsyncSignalInstance__name} of {owner_repr}>'


class AsyncSignal:
    attrs = ('__class_signals__', '__signals__', '__weakref__')

    def __init__(self, *types, isClassSignal: bool = False, use_priority: bool = False):
        self.__types = types
        self.__is_class_signal = isClassSignal
        self.__use_priority = use_priority
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
                owner.__class_signals__[self] = AsyncSignalBoundInstance(
                    self.__types, owner, self.__name,
                    is_class_signal=True,
                    use_priority=self.__use_priority,
                    context=context
                )
            return owner.__class_signals__[self]
        else:
            if not hasattr(instance, '__signals__'):
                instance.__signals__ = {}
            if self not in instance.__signals__:
                instance.__signals__[self] = AsyncSignalBoundInstance(
                    self.__types, instance, self.__name,
                    is_class_signal=False,
                    use_priority=self.__use_priority,
                    context=context
                )
            return instance.__signals__[self]

    def __set__(self, instance, value):
        raise AttributeError("AsyncSignal is read-only")
