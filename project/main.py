from flask import Flask, render_template, url_for

import api

app = Flask(__name__)


@app.route('/')
@app.route('/index')
def index():
    user = "Тестовая страница"
    return render_template('index.html', title='Домашняя страница',
                           username=user)

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')
