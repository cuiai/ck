#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from threading import Thread
import asyncio


def async_loop(func, *args, **kwargs):
    def makeUp(args, kwargs):
        return func(*args, **kwargs)

    eventLoop = asyncio.get_event_loop()
    future = eventLoop.run_in_executor(None, makeUp, args, kwargs)

    return future


def async_call(fn):
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()

    return wrapper


def async_called(fn):
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()

    return wrapper
