
from typing import Callable, Self, Any, Union
import time
import threading
import traceback
from DToolslib import EventSignal
from DToolslib.Color_Text import *


class JFTimer(threading.Thread):
    """

    """
    timeout = EventSignal()
    onError = EventSignal(Exception, str)
    terminated = EventSignal()
    __timer_dict__ = {}
    __create__lock = threading.Lock()

    def __new__(cls, name: str, *args, **kwargs) -> Self:
        if name not in cls.__timer_dict__:
            with cls.__create__lock:
                if name not in cls.__timer_dict__:
                    instance = super().__new__(cls)
                    cls.__timer_dict__[name] = instance
                    instance.__isInitialized__ = False
                    instance.__isAlived = False
                    instance.__name = name
        return cls.__timer_dict__[name]

    def __init__(self, name: str, interval: int | float = 0, callback: Callable[[], None] | list | tuple | None = None, on_error: Callable[[Exception, str], None] | list | tuple | None = None, daemon: bool = True) -> None:
        """
        Initialize the timer with a delay, function, and any additional arguments.
        """
        if self.__isInitialized__:
            return
        self.__isInitialized__ = True
        super().__init__(name=name, daemon=daemon)
        self.__name = name
        self.__interval: int | float = interval

        if isinstance(callback, (list, tuple)):
            for slot in callback:
                self.timeout.connect(slot)
        elif callback is not None and callable(callback):
            self.timeout.connect(callback)
        elif callback is None:
            pass
        else:
            e_text = ansi_color_text("callback must be callable or a list/tuple of callables", 31, bold=True)
            raise ValueError(e_text)

        if isinstance(on_error, (list, tuple)):
            for slot in on_error:
                self.onError.connect(slot)
        elif on_error is not None and callable(on_error):
            self.onError.connect(on_error)
        elif on_error is None:
            pass
        else:
            e_text = ansi_color_text("on_error must be callable or a list/tuple of callables", 31, bold=True)
            raise ValueError(e_text)

        self.__isAlived: bool = True
        self.__enableExecuteBeforeSleep = True
        self.__isStrictPeriod = True
        self.__kp: float = 0.35
        self.__ki: float = 0.02
        self.__kd: float = 0.25
        self.__integral_deviation: float = 0
        self.__integral_deviation_limit: float = self.__interval*0.1

        self.__attr_lock: threading.Lock = threading.Lock()
        self.__stop_event: threading.Event = threading.Event()
        self.__sleep_event: threading.Event = threading.Event()
        self.__stop_event.set()

        self.__correction_algorithm: Callable[[float], float] = self.__pid_control
        self.__time_adjust = 0
        self.__count: int = -1
        self.__current_count: int = 0  # 当前计数, 用于限制调用次数, 不具备统计功能
        self.__last_deviation: float = 0
        self.__exec_count: int = 0  # 统计执行次数, 实例化后不会再次清零
        self.__exec_duration = 0

    def __repr__(self) -> str:
        if not self.__isAlived:
            return f"<JFTimer <" + ansi_color_text(self.__name, 93) + "> has been " + ansi_color_text('terminated', 31, bold=True) + " (initialize required)>"
        else:
            return super().__repr__()

    @property
    def name(self) -> str:
        return self.__name

    @property
    def interval(self) -> int | float:
        return self.__interval

    @property
    def isRunning(self) -> bool:
        """ 
        @brief: timer is running or not
        """
        return not self.__stop_event.is_set() and self.__isAlived

    def enable_strict_period(self, enable: bool) -> Self:
        """ 
        enable strict period, if True, the timer will try to correct the deviation of the interval. if False, the timer will works as normal `threading.Timer`
        """
        with self.__attr_lock:
            self.__isStrictPeriod = enable
            return self

    def set_interval(self, interval: int | float, apply_immediately: bool = False) -> Self:
        """
        Set the interval for the timer.

        Args:
            interval: The interval for the timer.
        """
        if not isinstance(interval, (int, float)):
            e_text = ansi_color_text(f'interval must be int or float, but got {type(interval)}', 31)
            raise TypeError(e_text)
        isRunning: bool = not self.__stop_event.is_set()
        if isRunning and apply_immediately:
            self.stop()
        with self.__attr_lock:
            self.__interval = interval
            self.__integral_deviation_limit: float = self.__interval*0.1
        if apply_immediately:
            self.start()
        return self

    def set_count(self, count: int) -> Self:
        """
        Set the number of times the timer should run.

        Args:
            count: The number of times the timer should run. -1 means that it will run forever.
        """
        if not isinstance(count, int):
            e_text = ansi_color_text(f'count must be int, but got {type(count)}', 31)
            raise TypeError(e_text)
        with self.__attr_lock:
            self.__count = count
            self.__current_count = 0
        return self

    def enable_execute_before_sleep(self, flag: bool) -> Self:
        """
        Set whether to execute the callback function before sleeping.

        Args:
            flag: Whether to execute the callback function before sleeping.
        """
        if not isinstance(flag, bool):
            e_text = ansi_color_text(f'flag must be bool, but got {type(flag)}', 31)
            raise TypeError(e_text)
        isRunning: bool = not self.__stop_event.is_set()
        if isRunning:
            self.stop()
        with self.__attr_lock:
            self.__enableExecuteBeforeSleep: bool = flag
        if isRunning:
            self.start()
        return self

    def clear_current_count(self) -> None:
        """ 
        Clear the current count of the timer.
        """
        with self.__attr_lock:
            self.__current_count = 0

    def _set_pid_parameters(self, p: float, i: float, d: float) -> Self:
        """
        Set the PID parameters. 

        It is recommended to stop the timer before setting. 

        This function thread is not safe

        Args:
            p: Proportional coefficient.
            i: Integral coefficient.
            d: Differential coefficient.
        """
        if not (isinstance(p, (int, float)) and isinstance(i, (int, float)) and isinstance(d, (int, float))):
            e_text = ansi_color_text(f'p, i, d must be int or float, but got {type(p)}, {type(i)}, {type(d)}', 31)
            raise TypeError(e_text)
        self.__kp = p
        self.__ki = i
        self.__kd = d
        return self

    def set_correction_algorithm(self, algorithm: Callable[[float], float]) -> Self:
        """ 
        Set the correction algorithm. The default is PID control.

        Args:
            algorithm: A function that takes a float(current_deviation) as input and returns a float(output_correction).
                        if algorithm is None, the default PID control will be used.
        """
        if isinstance(algorithm, type(None)):
            self.__correction_algorithm = self.__pid_control
        elif callable(algorithm):
            self.__correction_algorithm: Callable[[float], float] = algorithm
        else:
            e_text = ansi_color_text(f'algorithm must be None or Callable, but got {type(algorithm)}', 31)
            raise TypeError(e_text)
        return self

    def run(self) -> None:
        while self.__isAlived:
            if self.__count >= 0 and self.__current_count >= self.__count:
                break
            self.__stop_event.wait()
            with self.__attr_lock:
                self.__start_time: float = time.perf_counter()
                interval = self.__interval
                if self.__count < 0:
                    pass
                elif self.__count > self.__current_count:
                    self.__current_count += 1
                else:
                    self.__isAlived = False
            if self.__isStrictPeriod:
                if self.__enableExecuteBeforeSleep:
                    self.__run_execution_before_sleep(interval=interval)
                else:
                    self.__run_execution_after_sleep(interval=interval)
            else:
                self.__run_execution_unstrict(interval=interval)
        self.terminate()

    def start(self, interval: float = None) -> None:
        """
        Start the timer.
        """
        if isinstance(interval, (float, int)):
            self.__interval = interval
        if self.__interval < 0:
            e_text = ansi_color_text(f"Interval must be greater than 0 or equal to 0, now it is {self.__interval}", 31)
            raise ValueError(e_text)
        if self.timeout.slot_counts < 1:
            e_text = ansi_color_text("No Callback function or signal slots", 31)
            raise ValueError(e_text)
        if not self.is_alive() and self.__isAlived:
            self.__stop_event.set()
            self.__sleep_event.clear()
            super().start()
        elif not self.is_alive() and not self.__isAlived:
            e_text = ansi_color_text("Timer is already terminated", 31, bold=True)
            raise RuntimeError(e_text)
        elif self.is_alive() and not self.__stop_event.is_set():
            self.__stop_event.set()
            self.__sleep_event.clear()
        else:
            print(ansi_color_text(f"Timer <{self.__name}>  is already started", 93))

    def stop(self) -> None:
        """
        Timer will stop immediately, it can be restarted by calling start() method
        """
        self.__stop_event.clear()
        self.__sleep_event.set()

    def terminate(self):
        """
        Timer will stop immediately and cannot be restarted
        """
        with self.__attr_lock:
            if not self.__isAlived:
                return
            self.__isAlived = False
            self.__stop_event.set()
            self.__sleep_event.set()
            with self.__class__.__create__lock:
                if self.__name in self.__class__.__timer_dict__:
                    del self.__class__.__timer_dict__[self.__name]
            self.terminated.emit()

    def __calculate_sleep_time(self, target_cycle_time: float, exec_duration: float) -> float:
        if target_cycle_time < 0:
            raise ValueError(ansi_color_text("target_cycle_time must be greater than 0 or equal to 0"), 31)
        elif target_cycle_time == 0:
            return 0
        sleep_time: float = target_cycle_time - exec_duration
        if sleep_time > 0:
            pass
        else:
            print(ansi_color_text(f"Timer <{self.__name}> is running late by {-sleep_time} seconds", 93, italic=True))
            if self.__isAlived and self.__interval > 0:
                raw_sleep_time: float = target_cycle_time - exec_duration % target_cycle_time
                sleep_time = raw_sleep_time - self.__time_adjust
                if sleep_time < 0:
                    sleep_time = raw_sleep_time
            elif self.__isAlived and self.__interval == 0:
                sleep_time = 1
            elif not self.__isAlived and self.__interval < 0:
                e_text = ansi_color_text(f"Timer interval can't be negative, now interval is {self.__interval}", 31, bold=True)
                raise ValueError(e_text)
            else:
                e_text = ansi_color_text("Timer is not alive, please start the Timer first", 32, bold=True)
                raise ValueError(e_text)
        return sleep_time

    def __pid_control(self, current_deviation: float) -> float:
        deviation_diff: float = current_deviation - self.__last_deviation
        self.__last_deviation = current_deviation
        self.__integral_deviation += current_deviation
        if self.__integral_deviation > self.__integral_deviation_limit:
            self.__integral_deviation = self.__integral_deviation_limit
        elif self.__integral_deviation < -self.__integral_deviation_limit:
            self.__integral_deviation = -self.__integral_deviation_limit

        kp_part: float = self.__kp * current_deviation
        ki_part: float = self.__ki * self.__integral_deviation
        kd_part: float = self.__kd * deviation_diff
        para: float = kp_part + ki_part + kd_part
        # test_text: str = ansi_color_text('kp', 31) + ':' + ansi_color_text(self.__kp, 32) + '\t' + ansi_color_text('ki', 31) + ':' + ansi_color_text(self.__ki, 32) + '\t' + ansi_color_text('kd', 31) + ':' + ansi_color_text(self.__kd, 32) + '\n' + \
        #     ansi_color_text('p', 36) + ':' + ansi_color_text(kp_part, 32) + '\t' + ansi_color_text('i', 36) + ':' + ansi_color_text(ki_part, 32) + '\t' + ansi_color_text('d', 36) + ':' + ansi_color_text(kd_part, 32) + '\t' + ansi_color_text('para', 36) + ':' + ansi_color_text(para, 32) + '\n' + \
        #     ansi_color_text('error', 33) + ':' + ansi_color_text(current_deviation, 32) + '\t' + ansi_color_text('error_diff', 33) + ':' + \
        #     ansi_color_text(deviation_diff, 32) + '\t' + ansi_color_text('integral_error', 33) + ':' + ansi_color_text(self.__integral_deviation, 32)
        # print(test_text)
        return para

    def __handle_error(self, error: Exception, traceback: str) -> None:
        if self.onError.slot_counts > 0:
            self.onError.emit(error, traceback)
            self.terminate()
        else:
            self.terminate()
            raise error

    def __run_execution_unstrict(self, interval: float) -> None:
        try:
            self.timeout.emit()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(ansi_color_text(f'Timer <{self.__name}> error: {traceback_str}', 31))
            self.__handle_error(error=e, traceback=traceback_str)
        self.__sleep_event.wait(timeout=interval)

    def __run_execution(self) -> None:
        try:
            self.timeout.emit()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(ansi_color_text(f'Timer <{self.__name}> error: {traceback_str}', 31))
            self.__handle_error(error=e, traceback=traceback_str)

    def __run_execution_before_sleep(self, interval: float) -> None:
        # 执行
        self.__run_execution()
        end_time: float = time.perf_counter()
        # 取数据, 用于计算时间
        with self.__attr_lock:
            self.__exec_duration: float = end_time - self.__start_time
            start_time: float = self.__start_time
            exec_duration: float = self.__exec_duration
            self.__exec_count += 1
        # 休眠
        sleep_time: float = self.__calculate_sleep_time(target_cycle_time=interval, exec_duration=exec_duration)
        if sleep_time > 0:
            self.__sleep_event.wait(timeout=sleep_time)
            # 优化下一次休眠时间
            current_diff: float = time.perf_counter() - start_time - interval
            self.__time_adjust: float = self.__correction_algorithm(current_diff)
            if not isinstance(self.__time_adjust, (float, int)):
                e_text: str = ansi_color_text(f'correction_algorithm must return a float, but got {type(self.__time_adjust)}', 31)
                raise ValueError(e_text)

    def __run_execution_after_sleep(self, interval: float):
        # 取数据, 用于计算时间
        with self.__attr_lock:
            start_time: float = self.__start_time
            exec_duration: float = self.__exec_duration
            self.__exec_count += 1
        # 休眠
        sleep_time: float = self.__calculate_sleep_time(target_cycle_time=interval, exec_duration=exec_duration)
        if sleep_time > 0:
            self.__sleep_event.wait(timeout=sleep_time)
        # 执行
        self.__run_execution()
        end_time: float = time.perf_counter()
        with self.__attr_lock:
            self.__exec_duration: float = end_time - self.__start_time
        if sleep_time > 0:
            # 优化下一次休眠时间
            current_diff: float = time.perf_counter() - start_time - interval
            self.__time_adjust: float = self.__correction_algorithm(current_diff)
            if not isinstance(self.__time_adjust, (float, int)):
                e_text: str = ansi_color_text(f'correction_algorithm must return a float, but got {type(self.__time_adjust)}', 31)
                raise ValueError(e_text)
