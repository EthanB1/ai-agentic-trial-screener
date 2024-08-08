# app/async_helper.py

import asyncio
from functools import wraps
from threading import Thread
import inspect

class AsyncToSync:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            coro = func(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result()
        elif inspect.isfunction(func) or inspect.ismethod(func):
            return self.loop.call_soon_threadsafe(func, *args, **kwargs)
        elif asyncio.iscoroutine(func):
            future = asyncio.run_coroutine_threadsafe(func, self.loop)
            return future.result()
        else:
            raise TypeError('A coroutine function, function, method, or coroutine object is required')

async_to_sync = AsyncToSync()

def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return async_to_sync.run_async(func, *args, **kwargs)
    return wrapper