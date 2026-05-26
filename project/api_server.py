from flask import Flask, request, jsonify
import sqlite3
from contextlib import contextmanager
import re

app = Flask(__name__)
DATABASE = 'phones.db'


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def normalize_phone(phone):
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    if not cleaned.startswith('+') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    return cleaned


@app.route('/api/phone/<phone_number>', methods=['GET'])
def get_phone_info(phone_number):
    """
    Получить имя владельца по номеру телефона
    Пример: GET /api/phone/79001234567
    """
    phone = normalize_phone(phone_number)

    with get_db() as conn:
        result = conn.execute(
            'SELECT phone, name FROM phones WHERE phone = ?',
            (phone,)
        ).fetchone()

    if result:
        return jsonify({
            "status": "success",
            "phone": result['phone'],
            "name": result['name']
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Номер {phone} не найден в базе"
        }), 404


@app.route('/api/phones', methods=['GET'])
def get_all_phones():
    """Получить список всех номеров и имён"""
    with get_db() as conn:
        phones = conn.execute(
            'SELECT phone, name FROM phones ORDER BY name'
        ).fetchall()

    return jsonify({
        "status": "success",
        "count": len(phones),
        "phones": [{"phone": p['phone'], "name": p['name']} for p in phones]
    })


@app.route('/api/phone', methods=['POST'])
def add_phone():
    """
    Добавить новый номер с именем
    Пример тела запроса:
    {
        "phone": "+79991234567",
        "name": "Дмитрий Козлов"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Нет данных"}), 400

    if 'phone' not in data:
        return jsonify({"status": "error", "message": "Не указан номер телефона"}), 400

    if 'name' not in data:
        return jsonify({"status": "error", "message": "Не указано имя владельца"}), 400

    phone = normalize_phone(data['phone'])
    name = data['name'].strip()

    if not name:
        return jsonify({"status": "error", "message": "Имя не может быть пустым"}), 400

    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO phones (phone, name) VALUES (?, ?)',
                (phone, name)
            )

        return jsonify({
            "status": "success",
            "message": f"Номер {phone} добавлен",
            "phone": phone,
            "name": name
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": f"Номер {phone} уже существует в базе"
        }), 409


@app.route('/api/phone/<phone_number>', methods=['PUT'])
def update_phone(phone_number):
    """
    Обновить имя владельца по номеру телефона
    Пример тела запроса:
    {
        "name": "Новое имя владельца"
    }
    """
    phone = normalize_phone(phone_number)
    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({
            "status": "error",
            "message": "Не указано новое имя"
        }), 400

    new_name = data['name'].strip()

    if not new_name:
        return jsonify({"status": "error", "message": "Имя не может быть пустым"}), 400

    with get_db() as conn:
        cursor = conn.execute(
            'UPDATE phones SET name = ? WHERE phone = ?',
            (new_name, phone)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": f"Номер {phone} не найден"
            }), 404

    return jsonify({
        "status": "success",
        "message": f"Имя для номера {phone} обновлено",
        "phone": phone,
        "name": new_name
    })


@app.route('/api/phone/<phone_number>', methods=['DELETE'])
def delete_phone(phone_number):
    """Удалить номер из базы"""
    phone = normalize_phone(phone_number)

    with get_db() as conn:
        result = conn.execute('SELECT name FROM phones WHERE phone = ?', (phone,)).fetchone()

        if not result:
            return jsonify({
                "status": "error",
                "message": f"Номер {phone} не найден"
            }), 404

        name = result['name']
        conn.execute('DELETE FROM phones WHERE phone = ?', (phone,))

    return jsonify({
        "status": "success",
        "message": f"Номер {phone} с именем '{name}' удален"
    })


@app.route('/api/search', methods=['GET'])
def search():
    """
    Поиск по номеру или имени
    Пример: GET /api/search?q=Иван
    Пример: GET /api/search?q=7900
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({
            "status": "error",
            "message": "Параметр 'q' обязателен"
        }), 400

    search_pattern = f"%{query}%"

    with get_db() as conn:
        results = conn.execute(
            '''SELECT phone, name 
               FROM phones 
               WHERE phone LIKE ? OR name LIKE ?
               ORDER BY name''',
            (search_pattern, search_pattern)
        ).fetchall()

    return jsonify({
        "status": "success",
        "query": query,
        "count": len(results),
        "results": [{"phone": r['phone'], "name": r['name']} for r in results]
    })


@app.route('/api/phones/batch', methods=['POST'])
def add_phones_batch():
    """
    Добавить несколько номеров сразу
    Пример тела запроса:
    {
        "phones": [
            {"phone": "+79991112233", "name": "Пользователь 1"},
            {"phone": "+79994445566", "name": "Пользователь 2"}
        ]
    }
    """
    data = request.get_json()

    if not data or 'phones' not in data:
        return jsonify({
            "status": "error",
            "message": "Необходимо передать массив phones"
        }), 400

    phones_list = data['phones']

    if not isinstance(phones_list, list):
        return jsonify({
            "status": "error",
            "message": "phones должен быть массивом"
        }), 400

    added = []
    failed = []

    with get_db() as conn:
        for item in phones_list:
            if 'phone' not in item or 'name' not in item:
                failed.append({
                    "item": item,
                    "error": "Отсутствует phone или name"
                })
                continue

            phone = normalize_phone(item['phone'])
            name = item['name'].strip()

            if not name:
                failed.append({
                    "item": item,
                    "error": "Имя не может быть пустым"
                })
                continue

            try:
                conn.execute(
                    'INSERT INTO phones (phone, name) VALUES (?, ?)',
                    (phone, name)
                )
                added.append({"phone": phone, "name": name})
            except sqlite3.IntegrityError:
                failed.append({
                    "item": item,
                    "error": f"Номер {phone} уже существует"
                })

    return jsonify({
        "status": "success",
        "added_count": len(added),
        "failed_count": len(failed),
        "added": added,
        "failed": failed
    })


if __name__ == '__main__':
    print("=" * 50)
    print("📱 API для базы номеров телефонов запущено")
    print("=" * 50)
    print("📖 Доступные эндпоинты:")
    print("  GET    /api/phones                  - получить все номера")
    print("  GET    /api/phone/<номер>           - получить имя по номеру")
    print("  POST   /api/phone                   - добавить номер и имя")
    print("  PUT    /api/phone/<номер>           - обновить имя по номеру")
    print("  DELETE /api/phone/<номер>           - удалить номер")
    print("  GET    /api/search?q=текст          - поиск по номеру или имени")
    print("  POST   /api/phones/batch            - массовое добавление номеров")
    print("=" * 50)
    print("🚀 Сервер запущен на http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
