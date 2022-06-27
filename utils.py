import time
import types

from facade import Context
from promise import Promise


def unwind(gen, ok, fail, ret=None, method='send'):
    try:
        ret = getattr(gen, method)(ret)
    except StopIteration as stop:
        return ok(stop.value)
    except Exception as e:
        return fail(e)

    if is_generator(ret):
        unwind(
            ret,
            ok=lambda x: unwind(gen, ok, fail, x),
            fail=lambda e: unwind(gen, ok, fail, e, 'throw'),
        )
    elif is_promise(ret):
        ret.then(
            lambda x=None: unwind(gen, ok, fail, x)
        ).catch(
            lambda e: unwind(gen, ok, fail, e, 'throw')
        )
    else:
        wait_all(
            ret,
            lambda x=None: unwind(gen, ok, fail, x),
            lambda e: unwind(gen, ok, fail, e, 'throw'),
        )


def wait_all(col, ok, fail):
    counter = len(col)
    results = [None] * counter

    def _resolve_single(i):
        def _do_resolve(val):
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
    return int(time.time() * 10e6)


def sleep(duration):
    return Context._event_loop.set_timer(duration * 10e3)