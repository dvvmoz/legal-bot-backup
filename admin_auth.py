"""
Модуль аутентификации для админ-панели.
"""
import os
import hashlib
import secrets
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, render_template

# Настройки аутентификации
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')

# Если пароль не задан, создаем дефолтный
if not ADMIN_PASSWORD_HASH:
    default_password = 'admin123'
    ADMIN_PASSWORD_HASH = hashlib.sha256(default_password.encode()).hexdigest()
    print(f"⚠️  ВНИМАНИЕ: Используется дефолтный пароль: {default_password}")
    print(f"   Для безопасности установите ADMIN_PASSWORD_HASH в .env файле")

def hash_password(password: str) -> str:
    """Хеширование пароля."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Проверка пароля."""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

def authenticate_user(username: str, password: str) -> bool:
    """Аутентификация пользователя."""
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
        session['authenticated'] = True
        session['username'] = username
        return True
    return False

def is_authenticated() -> bool:
    """Проверка аутентификации."""
    return session.get('authenticated', False)

def logout_user():
    """Выход пользователя."""
    session.pop('authenticated', None)
    session.pop('username', None)

def require_auth(f):
    """Декоратор для проверки аутентификации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json:
                return jsonify({'error': 'Требуется аутентификация', 'redirect': '/login'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def setup_auth_routes(app):
    """Настройка маршрутов аутентификации."""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Страница входа."""
        if request.method == 'POST':
            data = request.json if request.is_json else request.form
            username = data.get('username')
            password = data.get('password')
            
            if authenticate_user(username, password):
                if request.is_json:
                    return jsonify({'success': True, 'redirect': '/'})
                return redirect('/')
            else:
                if request.is_json:
                    return jsonify({'error': 'Неверные учетные данные'}), 401
                return render_template('admin/login.html', error='Неверные учетные данные')
        
        if is_authenticated():
            return redirect('/')
        
        return render_template('admin/login.html')
    
    @app.route('/logout')
    def logout():
        """Выход."""
        logout_user()
        return redirect('/login')
    
    @app.route('/api/auth/status')
    def auth_status():
        """Статус аутентификации."""
        return jsonify({
            'authenticated': is_authenticated(),
            'username': session.get('username') if is_authenticated() else None
        })

def generate_password_hash(password: str) -> str:
    """Генерация хеша пароля для .env файла."""
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == '__main__':
    # Утилита для генерации хеша пароля
    import sys
    if len(sys.argv) > 1:
        password = sys.argv[1]
        hash_value = generate_password_hash(password)
        print(f"Пароль: {password}")
        print(f"Хеш: {hash_value}")
        print(f"Добавьте в .env файл: ADMIN_PASSWORD_HASH={hash_value}")
    else:
        print("Использование: python admin_auth.py <пароль>")
        print("Пример: python admin_auth.py mypassword123") 