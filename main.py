import json
import random
import socket

from async_socket import async_socket
from event_loop import EventLoop
from facade import Context
from utils import sleep

from log import get_console

console = get_console(format='<bold>main</bold>{message}')


class Client:
    def __init__(self, addr):
        self.addr = addr

    def get_user(self, user_id):
        return self._get(f'GET user {user_id}\n')

    def get_balance(self, account_id):
        return self._get(f'GET account {account_id}\n')

    def _get(self, req):
        sock = async_socket(socket.AF_INET, socket.SOCK_STREAM)
        yield sock.connect(self.addr)
        try:
            yield sock.sendall(req.encode('utf8'))
            resp = yield sock.recv(1024)
            return json.loads(resp)
        finally:
            sock.close()


def get_user_balance(serv_addr, user_id):
    yield sleep(random.randint(0, 1000))

    client = Client(serv_addr)
    user = yield client.get_user(user_id)
    if user_id % 5 == 0:
        raise Exception('It is OK to throw here')
    acc = yield client.get_balance(user['account_id'])
    return f'User {user["name"]} has {acc["balance"]} USD'


def print_balance(serv_addr, user_id):
    try:
        balance = yield get_user_balance(serv_addr, user_id)
        print(balance)
    except Exception as exc:
        print('Catched:', exc)


def main1(serv_addr):
    console(f'.main1({serv_addr}')

    def on_sleep():
        console('.main1.on_sleep()')

        b = yield get_user_balance(serv_addr, 1)
        print('side flow:', b)  # <- до сюда вроде не доходит...

    # promise = sleep(5000)
    # promise.then(on_sleep)
    sleep(5000).then(on_sleep)

    tasks = []
    for i in range(10):
        tasks.append(print_balance(serv_addr, i))
    yield tasks  # может yield from?


def main2(*args):
    sock = async_socket(socket.AF_INET, socket.SOCK_STREAM)
    yield sock.connect(('info.cern.ch', 80))

    try:
        yield sock.sendall(b'GET / HTTP/1.1\r\nHost: info.cern.ch\r\n\r\n')
        val = yield sock.recv(1024)
        print(f'\n\n{val}\n\n')
    finally:
        sock.close()

def gather(tasks):
    yield tasks()

if __name__ == '__main__':
    # print('Run main1()')
    # event_loop = EventLoop()
    # Context.set_event_loop(event_loop)
    #
    # serv_addr = ('127.0.0.1', 53210)
    # event_loop.run(main1, serv_addr)

    # print('\nRun main2()')
    # event_loop = EventLoop()
    # Context.set_event_loop(event_loop)
    # event_loop.run(main2)


    event_loop = EventLoop()
    Context.set_event_loop(event_loop)
    event_loop.run(
        gather, main2
    )