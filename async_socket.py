import selectors

import errno
import socket

from facade import Context
from promise import Promise

from log import get_console

console = get_console(format='<light-green>async_socket</light-green>{message}')


class async_socket(Context):
    def __init__(self, *args):
        self._sock = socket.socket(*args)
        self._sock.setblocking(False)
        self._event_loop.register_fileobj(self._sock, self._on_event)
        self._state = self.states.INITIAL
        self._callbacks = {}

    def connect(self, addr):
        console(f'.connect(addr={addr})')

        if self._state != self.states.INITIAL:
            raise Exception(f'state {self.states.INITIAL} expected, but is {self._state}')

        self._state = self.states.CONNECTING

        p = Promise()

        def _on_conn(error):
            if error:
                p._reject(error)
            else:
                p._resolve()

        self._callbacks['conn'] = _on_conn

        error_code = self._sock.connect_ex(addr)

        if error_code != errno.EINPROGRESS:
            raise Exception('error code is not EINPROGRESS')

        return p

    def recv(self, n):
        console(f'.recv(n={n})')

        if self._state != self.states.CONNECTED:
            raise Exception(f'async_socket.recv(): self._state expected 2 but actual is {self._state}')

        if 'recv' in self._callbacks:
            raise Exception('async_socket.recv(): recv in self._callbacks')

        p = Promise()

        def _on_read_ready(error):
            if error:
                p._reject(error)
            else:
                data = self._sock.recv(n)
                p._resolve(data)

        self._callbacks['recv'] = _on_read_ready

        return p

    def sendall(self, data):
        console(f'.sendall(data={data})')

        if self._state != self.states.CONNECTED:
            raise Exception(f'async_socket.sendall(), self._state expected 2 but actual is {self._state}')

        if 'sent' in self._callbacks:
            raise Exception('async_socket.sendall(), sent in self._callbacks')

        p = Promise()

        def _on_write_ready(error):
            nonlocal data

            if error:
                return p._reject(error)

            n = self._sock.send(data)

            if n < len(data):
                data = data[n:]
                self._callbacks['sent'] = _on_write_ready
            else:
                p._resolve(None)

        self._callbacks['sent'] = _on_write_ready

        return p

    def close(self):
        self._event_loop.unregister_fileobj(self._sock)
        self._callbacks.clear()
        self._state = self.states.CLOSED
        self._sock.close()

    def _on_event(self, mask):
        if self._state == self.states.CONNECTING:
            console('._on_event: CONNECTING')

            if mask != selectors.EVENT_WRITE:
                raise Exception(
                    f'_on_event(): mask {selectors.EVENT_WRITE} expeted, but {mask} is actual'
                )
            callback = self._callbacks.pop('conn')
            error = self._get_sock_error()
            if error:
                self.close()
            else:
                self._state = self.states.CONNECTED
            callback(error)

        if mask & selectors.EVENT_READ:
            callback = self._callbacks.get('recv')

            if callback:
                del self._callbacks['recv']
                error = self._get_sock_error()
                callback(error)

        if mask & selectors.EVENT_WRITE:
            callback = self._callbacks.get('sent')

            if callback:
                del self._callbacks['sent']
                error = self._get_sock_error()
                callback(error)

    def _get_sock_error(self):
        console('._get_sock_error()')

        errorno = self._sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if errorno:
            return ConnectionError(
                f'connection failed: error: {errorno}, {errno.errorcode[errorno]}'
            )
