import time
import types

from facade import Context
from promise import Promise

from log import get_console, get_callable_representation

console = get_console(format='{message}')

unwind_console = get_console(format='<light-yellow>unwind</light-yellow>{message}')


def unwind(generator, on_success, on_exceptions, to_generator=None, method='send'):
    unwind_console(f'(gen={generator}, on_success={get_callable_representation(on_success)}, fail={get_callable_representation(on_exceptions)}, to_generator={to_generator}, method={method})')

    try:
        # пробуем пнуть герератор
        returned = getattr(generator, method)(to_generator)
        unwind_console(f': complete send to generator, returned={returned}')

    except StopIteration as stop:
        unwind_console(f': StopIteration, return {get_callable_representation(on_success)}({stop.value})')

        return on_success(stop.value) if on_success else None
    except Exception as e:
        unwind_console(f': Exception, return {get_callable_representation(on_exceptions)}({e})')

        return on_exceptions(e)

    if is_generator(returned):
        # generator вернул другой генератор

        unwind_console(f': to_generator is_generator')

        unwind(
            returned,
            on_success=lambda x: unwind(generator, on_success, on_exceptions, x),
            on_exceptions=lambda e: unwind(generator, on_success, on_exceptions, e, 'throw'),
        )
    elif is_promise(returned):
        unwind_console(': to_generator is_promise')

        returned.then(
            lambda x=None: unwind(generator, on_success, on_exceptions, x)
        ).catch(
            lambda e: unwind(generator, on_success, on_exceptions, e, 'throw')
        )
    else:
        unwind_console(': else')

        wait_all(
            returned,
            lambda x=None: unwind(generator, on_success, on_exceptions, x),
            lambda e: unwind(generator, on_success, on_exceptions, e, 'throw'),
        )


def wait_all(awaitables, ok, fail):
    """Ждем всех, когда последний ... - передаем results в on_success
    awaitables - collection?

    """
    counter = len(awaitables)

    def _resolve_single(i):
        def _do_resolve(val):
            """последний _do_resolve запустит on_success(results)"""
            nonlocal counter
            counter -= 1
            if counter == 0:
                ok(None)

        return _do_resolve

    for i, c in enumerate(awaitables):
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

    return Context.event_loop.set_timer(duration * 10e3)
