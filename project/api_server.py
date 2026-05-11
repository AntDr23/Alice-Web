import io
import logging
from contextlib import contextmanager, redirect_stdout
# from http.client import responses
# from json import dumps
from multiprocessing import Process
from time import sleep

from flask import Flask, abort, jsonify

from random import choice  # 🤤

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class Server:
    def __init__(self, host, port, daresponses):
        self.__host__ = host
        self.__port__ = port
        self.responses = daresponses

    @contextmanager
    def run(self):
        p = Process(target=self.server)
        p.start()
        sleep(1)
        yield
        p.kill()

    def generate_response(self):
        return jsonify(choice(self.responses))

    def server(self):
        _ = io.StringIO()
        with redirect_stdout(_):
            app = Flask(__name__)

            @app.route('/')
            def index():
                return f'use http://{self.__host__}:{self.__port__}/api/<number>/<api_key>'

            @app.route('/api')
            @app.route('/api/<number>')
            def api(number=None):
                if not number:
                    abort(400, description='no number/email')
                else:
                    return self.generate_response()

            app.run(self.__host__, self.__port__)


if __name__ == '__main__':
    daresponses = [
        {
            'response': {
                'is_safe': 1,
                'threat_index': 0,
                'reports': 0
            }
        }, {
            'response': {
                'is_safe': 0,
                'threat_index': 10,
                'reports': 67
            }
        }
    ]
    server = Server('127.0.0.1', 143, daresponses)
    with server.run():
        while (row := input('Введите "stop" для завершения работы сервера: ')) != 'stop':
            ...
