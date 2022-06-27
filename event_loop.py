from log import get_logger
from promise import Promise
from queue import Queue
from utils import hrtime, is_generator, unwind

logger = get_logger(format='EventLoop{message}')


class EventLoop:
    def __init__(self):
        self._queue = Queue()
        self._time = None

    def run(self, entry_point, *args):
        logger.info(f'run(entry_point={entry_point}, args={args}')

        self._execute(entry_point, *args)

        while not self._queue.is_empty():
            fn, mask = self._queue.pop(self._time)  # *mask
            self._execute(fn, mask)  # *mask

        self._queue.close()

    def register_fileobj(self, fileobj, callback):
        logger.info(f'.register_fileobj(fileobj={fileobj}, callback={callback})')

        self._queue.register_fileobj(fileobj, callback)

    def unregister_fileobj(self, fileobj):
        logger.info(f'.unregister_fileobj(fileobj={fileobj}')

        self._queue.unregister_fileobj(fileobj)

    def set_timer(self, duration):
        logger.info(f'.set_timer(duration={duration})')

        p = Promise()

        self._time = hrtime()

        self._queue.register_timer(
            self._time + duration,
            lambda _: p._resolve()
        )

        return p

    def _execute(self, callback, *args):
        logger.info(f'._execute(callback={callback}, args={args}')

        self._time = hrtime()  # по идее не нужно

        try:
            ret = callback(*args)

            if is_generator(ret):
                unwind(
                    ret,
                    ok=lambda *_: None,
                    fail=lambda e: print('Uncaught rejection:', e)
                )

        except Exception as exc:
            print('Uncaught exception:', exc)

        self._time = hrtime()
        logger.info(f'._execute end')
