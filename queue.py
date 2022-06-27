import collections
import heapq
import selectors
import time

from log import get_logger

logger = get_logger(format='Queue{message}')


class Queue:
    def __init__(self):
        self._selector = selectors.DefaultSelector()
        self._timers = []
        self._timer_no = 0
        self._ready = collections.deque()

    def register_timer(self, tick, callback):
        logger.info(f'.register_timer(tick={tick}, callback={callback})')

        timer = (tick, self._timer_no, callback)
        heapq.heappush(self._timers, timer)
        self._timer_no += 1

    def register_fileobj(self, fileobj, callback):
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(fileobj, events, callback)

    def unregister_fileobj(self, fileobj):
        self._selector.unregister(fileobj)

    def pop(self, tick):
        logger.info(f'.pop(tick={tick})')

        if self._ready:
            queue_element = self._ready.popleft()
            logger.info(f'.pop: Queue._ready not empty -> return {queue_element}')
            return queue_element

        timeout = self.get_timeout(tick)
        logger.info(f' timeout={timeout}')

        events = self.select(timeout)
        logger.info(f'.pop: events={events}')

        if events:
            logger.info('.pop appending events to _ready')
        else:
            logger.info('.pop No events')

        for key, mask in events:
            callback = key.data
            self._ready.append((callback, mask))

        if events:
            logger.info(f'._ready={self._ready}')

        if not self._ready and self._timers:
            idle = (self._timers[0][0] - tick)

            logger.info(f'._ready is empty, _timers={self._timers}')

            if idle > 0:
                logger.info(f'.pop sleeping for {idle / 10e6}')

                time.sleep(idle / 10e6)

                logger.info(f'.pop recursive call Queue.pop')
                queue_element = self.pop(tick + idle)

                logger.info(f'.pop returning {queue_element}')
                return queue_element

        while self._timers and self._timers[0][0] <= tick:
            *_, callback = heapq.heappop(self._timers)
            self._ready.append((callback, None))

        queue_element = self._ready.popleft()
        logger.info(f'.pop returning {queue_element}')
        return queue_element

    def select(self, timeout):
        logger.info(f'.select(timeout={timeout})')

        try:
            """Берем первый готовый сокет"""

            # logger.info('Queue.select trying get event by timeout')
            events = self._selector.select(timeout)
        except OSError:
            # logger.info(f'Qeue.select error - sleeping for {timeout}')

            time.sleep(timeout)
            events = tuple()

        return events

    def get_timeout(self, tick):
        logger.info(f'Queue.get_timeout(tick={tick})')
        return (self._timers[0][0] - tick) / 10e6 if self._timers else None

    def is_empty(self):
        return not (self._ready or self._timers or self._selector.get_map())

    def close(self):
        self._selector.close()
