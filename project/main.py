from flask import Flask, render_template, url_for, request
import requests

import api_server

app = Flask(__name__)
resultt = None

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    user = "Тестовая страница"
    global resultt
    if request.method == 'POST':
        try:
            tel = '+7' + str(request.form.get("number"))
            print(tel)
            response = requests.get(f"http://localhost:5000/api/phone/{tel}")
            print(response.json())
            if response.status_code == 200:
                data = response.json()
                print(f"Имя владельца: {data['name']}")
                if data["name"].lower() != "спам":
                    resultt = "safe"
                else:
                    resultt = "unsafe"
            else:
                print(f"Номер {tel} не найден в базе")
                resultt = "nonum"
            print(resultt)
        except Exception as e:
            print(e)
    return render_template('index.html', title='Домашняя страница', result=resultt)


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')
