from flask import Flask, request, jsonify
import sqlite3
from contextlib import contextmanager
import re

app = Flask(__name__)
DATABASE = 'phones.db'

# ========== Работа с базой данных ==========
def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS phones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                operator TEXT,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        conn.execute('CREATE INDEX IF NOT EXISTS idx_phone ON phones(phone)')
        cursor = conn.execute('SELECT COUNT(*) FROM phones')
        if cursor.fetchone()[0] == 0:
            test_data = [
                ("+79001234567", "Иван Петров", "МТС", "Москва"),
                ("+79161234567", "Мария Сидорова", "Мегафон", "Санкт-Петербург"),
                ("+79251234567", "Алексей Иванов", "Билайн", "Казань"),
                ("+79371234567", "Елена Смирнова", "Tele2", "Новосибирск"),
            ]
            conn.executemany(
                'INSERT INTO phones (phone, name, operator, region) VALUES (?, ?, ?, ?)',
                test_data
            )
        conn.commit()

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
    """Нормализация телефонного номера"""
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    if not cleaned.startswith('+') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    
    return cleaned

# ========== API Endpoints ==========
@app.route('/api/phone/<phone_number>', methods=['GET'])
def get_phone_info(phone_number):
    """Получить информацию о номере телефона"""
    phone = normalize_phone(phone_number)
    with get_db() as conn:
        result = conn.execute(
            'SELECT phone, name, operator, region, created_at, updated_at FROM phones WHERE phone = ?',
            (phone,)
        ).fetchone()
    if result:
        return jsonify({
            "status": "success",
            "data": dict(result)
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Номер {phone} не найден в базе"
        }), 404

@app.route('/api/phones', methods=['GET'])
def get_all_phones():
    """Получить список всех номеров с пагинацией"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM phones').fetchone()[0]
        
        phones = conn.execute(
            'SELECT phone, name, operator, region FROM phones LIMIT ? OFFSET ?',
            (per_page, offset)
        ).fetchall()
    
    return jsonify({
        "status": "success",
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        },
        "phones": [dict(phone) for phone in phones]
    })

@app.route('/api/phone', methods=['POST'])
def add_phone():
    """Добавить новый номер"""
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "Нет данных"}), 400
    
    required_fields = ['phone', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"Отсутствует обязательное поле: {field}"
            }), 400
    
    phone = normalize_phone(data['phone'])
    name = data['name']
    operator = data.get('operator', '')
    region = data.get('region', '')
    
    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO phones (phone, name, operator, region) VALUES (?, ?, ?, ?)',
                (phone, name, operator, region)
            )
        
        return jsonify({
            "status": "success",
            "message": f"Номер {phone} добавлен",
            "data": {"phone": phone, "name": name}
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": f"Номер {phone} уже существует в базе"
        }), 409

@app.route('/api/phone/<phone_number>', methods=['PUT'])
def update_phone(phone_number):
    """Обновить информацию о номере"""
    phone = normalize_phone(phone_number)
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "Нет данных для обновления"}), 400
    
    updates = []
    values = []
    
    for field in ['name', 'operator', 'region']:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])
    
    if not updates:
        return jsonify({"status": "error", "message": "Нет полей для обновления"}), 400
    
    values.append(phone)
    query = f"UPDATE phones SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE phone = ?"
    
    with get_db() as conn:
        cursor = conn.execute(query, values)
        
        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": f"Номер {phone} не найден"
            }), 404
    
    return jsonify({
        "status": "success",
        "message": f"Номер {phone} обновлен"
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
        "message": f"Номер {phone} ({name}) удален"
    })

@app.route('/api/search', methods=['GET'])
def search():
    """Поиск по имени или номеру"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            "status": "error",
            "message": "Параметр 'q' обязателен"
        }), 400
    
    search_pattern = f"%{query}%"
    
    with get_db() as conn:
        results = conn.execute(
            '''SELECT phone, name, operator, region 
               FROM phones 
               WHERE phone LIKE ? OR name LIKE ?
               ORDER BY name''',
            (search_pattern, search_pattern)
        ).fetchall()
    
    return jsonify({
        "status": "success",
        "query": query,
        "count": len(results),
        "results": [dict(result) for result in results]
    })

# ========== Инициализация и запуск ==========
if __name__ == '__main__':
    init_db()
    print("🚀 API запущено на http://localhost:5000")
    print("📖 Доступные эндпоинты:")
    print("  GET    /api/phones              - получить все номера")
    print("  GET    /api/phone/<номер>       - получить информацию о номере")
    print("  POST   /api/phone               - добавить номер")
    print("  PUT    /api/phone/<номер>       - обновить номер")
    print("  DELETE /api/phone/<номер>       - удалить номер")
    print("  GET    /api/search?q=текст      - поиск")
    app.run(debug=True, host='0.0.0.0', port=5000)
