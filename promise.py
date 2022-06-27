from facade import Context

from log import get_logger

logger = get_logger(format='Promise{message}')


class Promise(Context):
    def __init__(self):
        logger.info('.__init__()')

        self._on_resolve = []
        self._on_reject = []
        self._resolved = False
        self._rejected = False
        self._value = None

    # вроде это пока не используется
    # @classmethod
    # def all(cls, promises):
    #     logger.info(f'.all({promises})')
    #
    #     pall = cls()
    #     counter = len(promises)
    #
    #     if counter == 0:
    #         pall._resolve()
    #         return pall
    #
    #     results = [None] * counter
    #
    #     def _on_single_resolved(i):
    #         def _callback(*args):
    #             nonlocal counter
    #
    #             results[i] = args
    #             counter -= 1
    #             if counter == 0:
    #                 pall._resolve(results)
    #
    #         return _callback
    #
    #     for idx, p in enumerate(promises):
    #         p.then(_on_single_resolved(idx))
    #         p.catch(pall._reject)
    #
    #     return pall

    def then(self, callback):
        if self._resolved:
            self._event_loop._execute(callback, *self._value)
        elif not self._rejected:
            self._on_resolve.append(callback)
        return self

    def catch(self, callback):
        if self._rejected:
            self._event_loop._execute(callback, self._value)
        elif not self._resolved:
            self._on_reject.append(callback)
        return self

    def _resolve(self, *args):
        if self._resolved or self._rejected:
            return

        self._resolved = True
        self._value = args

        for callback in self._on_resolve:
            self._event_loop._execute(callback, *args)

    def _reject(self, error):
        if self._resolved or self._rejected:
            return

        self._rejected = True
        self._value = error

        for callback in self._on_reject:
            callback(error)
