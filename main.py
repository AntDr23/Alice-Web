from flask import Flask, request, jsonify
import logging
import json

app = Flask(__name__)

# Добавляем логирование в файл. 
# Чтобы найти файл, перейдите на pythonwhere в раздел files, 
# он лежит в корневой папке
logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Request: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:  # начало диалога
        res['response']['text'] = \
            'Привет! Я могу показать город или сказать расстояние между городами!'
        return
    # TODO всю логику навыка


if __name__ == '__main__':
    app.run()
