import time
import types

from facade import Context
from promise import Promise

from log import get_console, get_callable_representation

console = get_console(format='{message}')

unwind_console = get_console(format='<light-yellow>unwind</light-yellow>{message}')


def unwind(gen, on_success, on_exceptions, ret=None, method='send'):
    unwind_console(f'(gen={gen}, on_success={get_callable_representation(on_success)}, fail={get_callable_representation(on_exceptions)}, ret={ret}, method={method})')

    try:
        # пробуем пнуть герератор
        ret = getattr(gen, method)(ret)
        unwind_console(f': start generator, ret={ret}')

    except StopIteration as stop:
        unwind_console(f': StopIteration, return {get_callable_representation(on_success)}({stop.value})')

        return on_success(stop.value)
    except Exception as e:
        unwind_console(f': Exception, return {get_callable_representation(on_exceptions)}({e})')

        return on_exceptions(e)

    if is_generator(ret):
        # gen вернул другой генератор

        unwind_console(f': ret is_generator')

        unwind(
            ret,
            on_success=lambda x: unwind(gen, on_success, on_exceptions, x),
            on_exceptions=lambda e: unwind(gen, on_success, on_exceptions, e, 'throw'),
        )
    elif is_promise(ret):
        unwind_console(': ret is_promise')

        ret.then(
            lambda x=None: unwind(gen, on_success, on_exceptions, x)
        ).catch(
            lambda e: unwind(gen, on_success, on_exceptions, e, 'throw')
        )
    else:
        unwind_console(': else')

        wait_all(
            ret,
            lambda x=None: unwind(gen, on_success, on_exceptions, x),
            lambda e: unwind(gen, on_success, on_exceptions, e, 'throw'),
        )


def wait_all(col, ok, fail):
    """Ждем всех, когда последний ... - передаем results в on_success
    col - collection?

    """
    counter = len(col)
    results = [None] * counter

    def _resolve_single(i):
        def _do_resolve(val):
            """последний _do_resolve запустит on_success(results)"""
            nonlocal counter
            results[i] = val
            counter -= 1
            if counter == 0:
                ok(results)

        return _do_resolve

    for i, c in enumerate(col):
        if is_generator(c):
            unwind(c, on_success=_resolve_single(i), on_exceptions=fail)
            continue

        if is_promise(c):
            c.then(
                _resolve_single(i)
            ).catch(
                fail
            )
            continue

        raise Exception('Only promise or generator can be yielded to event loop')


def is_generator(val):
    return isinstance(val, types.GeneratorType)


def is_promise(val):
    return isinstance(val, Promise)


def hrtime():
    """high-resolution real time"""
    return int(time.time() * 10e6)


def sleep(duration) -> Promise:
    console(f'sleep({duration})')

    return Context._event_loop.set_timer(duration * 10e3)