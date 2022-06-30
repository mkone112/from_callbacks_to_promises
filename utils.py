import time
import types

from facade import Context
from promise import Promise

from log import get_console, get_callable_representation

console = get_console(format='{message}')

unwind_console = get_console(format='<light-yellow>unwind</light-yellow>{message}')


def unwind(gen, ok, fail, ret=None, method='send'):
    unwind_console(f'(gen={gen}, ok={get_callable_representation(ok)}, fail={get_callable_representation(fail)}, ret={ret}, method={method})')

    try:
        # пробуем пнуть герератор
        ret = getattr(gen, method)(ret)
        unwind_console(f': start generator, ret={ret}')

    except StopIteration as stop:
        unwind_console(f': StopIteration, return {get_callable_representation(ok)}({stop.value})')

        return ok(stop.value)
    except Exception as e:
        unwind_console(f': Exception, return {get_callable_representation(fail)}({e})')

        return fail(e)

    if is_generator(ret):
        # gen вернул другой генератор

        unwind_console(f': ret is_generator')

        unwind(
            ret,
            ok=lambda x: unwind(gen, ok, fail, x),
            fail=lambda e: unwind(gen, ok, fail, e, 'throw'),
        )
    elif is_promise(ret):
        unwind_console(': ret is_promise')

        ret.then(
            lambda x=None: unwind(gen, ok, fail, x)
        ).catch(
            lambda e: unwind(gen, ok, fail, e, 'throw')
        )
    else:
        unwind_console(': else')

        wait_all(
            ret,
            lambda x=None: unwind(gen, ok, fail, x),
            lambda e: unwind(gen, ok, fail, e, 'throw'),
        )


def wait_all(col, ok, fail):
    """Ждем всех, когда последний ... - передаем results в ok
    col - collection?

    """
    counter = len(col)
    results = [None] * counter

    def _resolve_single(i):
        def _do_resolve(val):
            """последний _do_resolve запустит ok(results)"""
            nonlocal counter
            results[i] = val
            counter -= 1
            if counter == 0:
                ok(results)

        return _do_resolve

    for i, c in enumerate(col):
        if is_generator(c):
            unwind(c, ok=_resolve_single(i), fail=fail)
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