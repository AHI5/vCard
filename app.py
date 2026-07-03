from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory, Response
from flask_cors import CORS
from functools import wraps
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import string
import random
import os
import time
import base64
from dotenv import load_dotenv

from db import (
    get_user_by_email,
    create_user,
    get_card_by_code,
    activate_card,
    get_profile_by_user_id,
    create_or_update_profile,
    get_card_by_user_id,
    get_visit_stats_by_user_id,
    execute_query,
    record_visit,
    get_all_users,
    get_all_cards,
    get_all_visits,
    get_all_profiles,
    get_admin_stats,
    delete_user,
    delete_card,
    update_card_status,
    unlink_card,
    update_profile,
    reset_user_password,
    create_card,
    create_cards_bulk,
    generate_next_codes
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-me')
CORS(app)

app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SITE_URL = os.getenv('SITE_URL', 'http://localhost:5000')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'photos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

ALLOWED_EMAIL_DOMAINS = {
    'mail.ru', 'list.ru', 'inbox.ru', 'bk.ru', 'me.com',
    'yandex.ru', 'yandex.com', 'ya.ru', 'yandex.by', 'yandex.kz',
    'rambler.ru', 'lenta.ru', 'autorambler.ru', 'ro.ru',
    'vk.com',
    'sputnik.ru',
    'internet.ru',
}

CARD_THEME_PRESETS = {
    'indigo': {'bg': '#f7fafc', 'button': '#5a67d8', 'name': 'Индиго'},
    'ocean': {'bg': '#ebf8ff', 'button': '#2b6cb0', 'name': 'Океан'},
    'forest': {'bg': '#f0fff4', 'button': '#2f855a', 'name': 'Лес'},
    'sunset': {'bg': '#fffaf0', 'button': '#c05621', 'name': 'Закат'},
    'rose': {'bg': '#fff5f7', 'button': '#b83280', 'name': 'Роза'},
    'midnight': {'bg': '#1a202c', 'button': '#63b3ed', 'name': 'Полночь'},
    'lavender': {'bg': '#faf5ff', 'button': '#6b46c1', 'name': 'Лаванда'},
    'mint': {'bg': '#e6fffa', 'button': '#319795', 'name': 'Мята'},
    'coral': {'bg': '#fff5f5', 'button': '#e53e3e', 'name': 'Коралл'},
    'gold': {'bg': '#fffff0', 'button': '#b7791f', 'name': 'Золото'},
    'slate': {'bg': '#f7fafc', 'button': '#4a5568', 'name': 'Сланец'},
    'peach': {'bg': '#fffaf0', 'button': '#ed8936', 'name': 'Персик'},
    'sky': {'bg': '#ebf8ff', 'button': '#4299e1', 'name': 'Небо'},
    'emerald': {'bg': '#f0fff4', 'button': '#38a169', 'name': 'Изумруд'},
    'plum': {'bg': '#faf5ff', 'button': '#9f7aea', 'name': 'Слива'},
    'charcoal': {'bg': '#2d3748', 'button': '#f6e05e', 'name': 'Уголь'}
}

def is_valid_russian_email(email):
    if not email or '@' not in email:
        return False, 'Некорректный формат email'
    domain = email.split('@')[1].lower()
    if domain.endswith('.ru'):
        return True, None
    if domain in ALLOWED_EMAIL_DOMAINS:
        return True, None
    return False, 'Разрешены только российские почтовые сервисы'

def get_allowed_domains_text():
    return """Разрешённые почтовые сервисы:
- Mail.ru (@mail.ru, @list.ru, @inbox.ru, @bk.ru)
- Яндекс (@yandex.ru, @ya.ru)
- Рамблер (@rambler.ru)
- VK (@vk.com)
- Sputnik (@sputnik.ru)
- Любой корпоративный домен .ru"""

def generate_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_activation_email(email, password):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = 'Ваша NFC-визитка активирована'
        login_url = f"{SITE_URL}/login"
        body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f5f7fa;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06);">
                <div style="background: #f7fafc; padding: 30px; text-align: center; border-bottom: 1px solid #e2e8f0;">
                    <h1 style="color: #2d3748; margin: 0; font-size: 22px; font-weight: 600;">Виртуальные визитки</h1>
                </div>
                <div style="padding: 30px;">
                    <h2 style="color: #2d3748; margin-top: 0; font-size: 20px; font-weight: 600;">Ваша NFC-визитка активирована</h2>
                    <p style="color: #4a5568; line-height: 1.6;">Здравствуйте!</p>
                    <p style="color: #4a5568; line-height: 1.6;">Ваша NFC-визитка успешно активирована. Вот ваши данные для входа в личный кабинет:</p>
                    <div style="background: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
                        <p style="margin: 10px 0; color: #2d3748;"><strong>Логин:</strong> <span style="color: #5a67d8;">{email}</span></p>
                        <p style="margin: 10px 0; color: #2d3748;"><strong>Пароль:</strong> <code style="background: white; padding: 5px 10px; border-radius: 4px; font-size: 15px; border: 1px solid #e2e8f0;">{password}</code></p>
                    </div>
                    <p style="color: #4a5568; line-height: 1.6;"><strong>Ссылка для входа:</strong><br>
                    <a href="{login_url}" style="color: #5a67d8;">{login_url}</a></p>
                    <p style="color: #4a5568; line-height: 1.6;">После входа заполните свой профиль — и ваша визитка будет готова к использованию.</p>
                    <p style="color: #4a5568; line-height: 1.6;">Сохраните эти данные в безопасном месте.</p>
                </div>
                <div style="background: #f7fafc; padding: 20px; text-align: center; color: #a0aec0; font-size: 12px; border-top: 1px solid #e2e8f0;">
                    <p>С уважением,<br>Команда Виртуальные визитки</p>
                    <p style="margin-top: 10px;">Это письмо отправлено автоматически, отвечать на него не нужно.</p>
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Письмо успешно отправлено на {email}")
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Требуется авторизация'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Требуется авторизация'}), 401
            return redirect('/login')
        user_email = session.get('user_email', '')
        admin_emails = os.getenv('ADMIN_EMAILS', '')
        admins = [email.strip().lower() for email in admin_emails.split(',') if email.strip()]
        if user_email.lower() not in admins:
            return jsonify({'error': 'Доступ запрещён. Вы не администратор.'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect('/activate')

@app.route('/activate')
def activate_page():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл index.html не найден", 404

@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        activation_code = data.get('activationCode', '').strip()
        if not email or not activation_code:
            return jsonify({'error': 'Заполните все поля'}), 400
        is_valid, error_msg = is_valid_russian_email(email)
        if not is_valid:
            return jsonify({'error': error_msg, 'allowedDomains': get_allowed_domains_text()}), 400
        card = get_card_by_code(activation_code)
        if not card:
            return jsonify({'error': 'Неверный код активации'}), 400
        if card['status'] != 'free':
            if card['status'] == 'activated':
                return jsonify({'error': 'Этот код уже был использован'}), 400
            elif card['status'] == 'blocked':
                return jsonify({'error': 'Этот код заблокирован'}), 400
        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'Этот email уже зарегистрирован. Используйте другой или войдите в личный кабинет.'}), 400
        password = generate_password()
        password_hash = generate_password_hash(password)
        user_id = create_user(email, password_hash)
        if not user_id:
            return jsonify({'error': 'Ошибка создания пользователя. Попробуйте позже.'}), 500
        activate_result = activate_card(activation_code, user_id)
        if activate_result == 0:
            execute_query("DELETE FROM users WHERE id = %s", (user_id,))
            return jsonify({'error': 'Не удалось активировать карту. Возможно, она уже используется.'}), 500
        email_sent = send_activation_email(email, password)
        if email_sent:
            return jsonify({'message': 'Карта успешно активирована', 'email': email}), 200
        else:
            print(f"Пользователь {email} создан, но письмо не отправлено")
            return jsonify({'message': 'Карта активирована, но возникли проблемы с отправкой письма. Обратитесь в поддержку.', 'email': email}), 207
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.json
    email = data.get('email', '').strip().lower()
    is_valid, error_msg = is_valid_russian_email(email)
    return jsonify({'valid': is_valid, 'error': error_msg, 'allowedDomains': get_allowed_domains_text() if not is_valid else None})

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect('/cabinet')
    try:
        with open('login.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл login.html не найден", 404

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        if not email or not password:
            return jsonify({'error': 'Заполните все поля'}), 400
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'Неверный email или пароль'}), 401
        if not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Неверный email или пароль'}), 401
        session.permanent = True
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        return jsonify({'message': 'Вход выполнен успешно', 'redirect': '/cabinet'}), 200
    except Exception as e:
        print(f"Ошибка входа: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/cabinet')
@login_required
def cabinet_page():
    try:
        with open('cabinet.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл cabinet.html не найден", 404

@app.route('/uploads/photos/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/backgrounds/<filename>')
def uploaded_bg(filename):
    bg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'backgrounds')
    return send_from_directory(bg_folder, filename)

@app.route('/api/user-info')
@login_required
def user_info():
    try:
        user_id = session.get('user_id')
        profile = get_profile_by_user_id(user_id)
        card = get_card_by_user_id(user_id)
        stats = get_visit_stats_by_user_id(user_id)
        response = {
            'email': session.get('user_email'),
            'user_id': user_id,
            'profile': profile,
            'card_code': card['activation_code'] if card else None,
            'stats': {
                'total_visits': stats['total_visits'] or 0,
                'last_visit': stats['last_visit'].isoformat() if stats['last_visit'] else None
            }
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"Ошибка получения информации: {e}")
        return jsonify({'error': 'Ошибка загрузки данных'}), 500

@app.route('/api/save-profile', methods=['POST'])
@login_required
def save_profile():
    try:
        user_id = session.get('user_id')
        data = request.json
        required_fields = ['first_name', 'last_name', 'phone', 'email']
        for field in required_fields:
            if not data.get(field, '').strip():
                return jsonify({'error': f'Поле "{field}" обязательно для заполнения'}), 400
        phone = data.get('phone', '').strip()
        phone_clean = ''.join(filter(str.isdigit, phone))
        if len(phone_clean) < 10:
            return jsonify({'error': 'Некорректный номер телефона'}), 400
        email = data.get('email', '').strip().lower()
        if '@' not in email:
            return jsonify({'error': 'Некорректный email'}), 400
        theme_preset = data.get('theme_preset', 'indigo')
        if theme_preset != 'custom' and theme_preset not in CARD_THEME_PRESETS:
            theme_preset = 'indigo'
        def is_valid_color(color):
            if not color:
                return False
            return color.startswith('#') and len(color) in [4, 7]
        bg_color = data.get('bg_color', '#f7fafc')
        if not is_valid_color(bg_color):
            bg_color = '#f7fafc'
        button_color = data.get('button_color', '#5a67d8')
        if not is_valid_color(button_color):
            button_color = '#5a67d8'
        button_language = data.get('button_language', 'ru')
        if button_language not in ['ru', 'en']:
            button_language = 'ru'
        gradient_direction = data.get('gradient_direction', '135deg')
        valid_directions = ['to right', 'to left', 'to top', 'to bottom', '45deg', '90deg', '135deg', '180deg', '225deg', '270deg', '315deg']
        if gradient_direction not in valid_directions:
            gradient_direction = '135deg'
        profile_data = {
            'first_name': data.get('first_name', '').strip(),
            'middle_name': data.get('middle_name', '').strip() or None,
            'last_name': data.get('last_name', '').strip(),
            'company': data.get('company', '').strip() or None,
            'position': data.get('position', '').strip() or None,
            'phone': phone,
            'email': email,
            'photo_url': data.get('photo_url'),
            'theme_preset': theme_preset,
            'bg_color': bg_color,
            'button_color': button_color,
            'bg_image_url': data.get('bg_image_url'),
            'button_language': button_language,
            'show_avatar': data.get('show_avatar', True),
            'gradient_enabled': data.get('gradient_enabled', False),
            'gradient_color1': data.get('gradient_color1', '#667eea'),
            'gradient_color2': data.get('gradient_color2', '#764ba2'),
            'gradient_direction': gradient_direction,
            'social_telegram': data.get('social_telegram', '').strip() or None,
            'social_instagram': data.get('social_instagram', '').strip() or None,
            'social_whatsapp': data.get('social_whatsapp', '').strip() or None,
            'social_vk': data.get('social_vk', '').strip() or None,
            'social_max': data.get('social_max', '').strip() or None,
        }
        result = create_or_update_profile(user_id, profile_data)
        if result is None:
            return jsonify({'error': 'Ошибка сохранения профиля'}), 500
        return jsonify({'message': 'Профиль успешно сохранён', 'profile': profile_data}), 200
    except Exception as e:
        print(f"Ошибка сохранения профиля: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    try:
        user_id = session.get('user_id')
        if 'photo' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Разрешены только файлы: PNG, JPG, JPEG, WEBP'}), 400
        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"user_{user_id}_{int(time.time())}.{extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        photo_url = f"/uploads/photos/{unique_filename}"
        existing_profile = get_profile_by_user_id(user_id)
        if existing_profile:
            if existing_profile.get('photo_url'):
                old_filename = existing_profile['photo_url'].split('/')[-1]
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                if os.path.exists(old_filepath):
                    try:
                        os.remove(old_filepath)
                    except Exception as e:
                        print(f"Ошибка удаления старого фото: {e}")
            execute_query("UPDATE profiles SET photo_url = %s WHERE user_id = %s", (photo_url, user_id))
        return jsonify({'message': 'Фото успешно загружено', 'photo_url': photo_url}), 200
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/delete-photo', methods=['POST'])
@login_required
def delete_photo():
    try:
        user_id = session.get('user_id')
        profile = get_profile_by_user_id(user_id)
        if not profile or not profile.get('photo_url'):
            return jsonify({'error': 'Фото не найдено'}), 404
        filename = profile['photo_url'].split('/')[-1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        execute_query("UPDATE profiles SET photo_url = NULL WHERE user_id = %s", (user_id,))
        return jsonify({'message': 'Фото удалено'}), 200
    except Exception as e:
        print(f"Ошибка удаления фото: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/upload-bg-image', methods=['POST'])
@login_required
def upload_bg_image():
    try:
        user_id = session.get('user_id')
        if 'image' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Разрешены только файлы: PNG, JPG, JPEG, WEBP'}), 400
        bg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'backgrounds')
        os.makedirs(bg_folder, exist_ok=True)
        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"bg_{user_id}_{int(time.time())}.{extension}"
        filepath = os.path.join(bg_folder, unique_filename)
        file.save(filepath)
        image_url = f"/uploads/backgrounds/{unique_filename}"
        existing_profile = get_profile_by_user_id(user_id)
        if existing_profile and existing_profile.get('bg_image_url'):
            old_filename = existing_profile['bg_image_url'].split('/')[-1]
            old_filepath = os.path.join(bg_folder, old_filename)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except Exception as e:
                    print(f"Ошибка удаления старого фона: {e}")
        return jsonify({'message': 'Фон загружен', 'image_url': image_url}), 200
    except Exception as e:
        print(f"Ошибка загрузки фона: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/delete-bg-image', methods=['POST'])
@login_required
def delete_bg_image():
    try:
        user_id = session.get('user_id')
        profile = get_profile_by_user_id(user_id)
        if not profile or not profile.get('bg_image_url'):
            return jsonify({'error': 'Изображение не найдено'}), 404
        bg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'backgrounds')
        filename = profile['bg_image_url'].split('/')[-1]
        filepath = os.path.join(bg_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        execute_query("UPDATE profiles SET bg_image_url = NULL WHERE user_id = %s", (user_id,))
        return jsonify({'message': 'Фон удалён'}), 200
    except Exception as e:
        print(f"Ошибка удаления фона: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Выход выполнен'}), 200

@app.route('/api/check-auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'email': session.get('user_email')}), 200
    return jsonify({'authenticated': False}), 200

def generate_vcard(profile):
    middle = profile.get('middle_name') or ''
    full_name = f"{profile['first_name']} {middle} {profile['last_name']}".replace('  ', ' ').strip()
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{profile['last_name']};{profile['first_name']};{middle};;",
        f"FN:{full_name}",
    ]
    if profile.get('company'):
        vcard_lines.append(f"ORG:{profile['company']}")
    if profile.get('position'):
        vcard_lines.append(f"TITLE:{profile['position']}")
    vcard_lines.append(f"TEL;TYPE=CELL:{profile['phone']}")
    vcard_lines.append(f"EMAIL:{profile['email']}")
    if profile.get('social_telegram'):
        tg = profile['social_telegram'].lstrip('@')
        vcard_lines.append(f"URL:https://t.me/{tg}")
    if profile.get('social_instagram'):
        ig = profile['social_instagram'].lstrip('@')
        vcard_lines.append(f"X-SOCIALPROFILE;TYPE=instagram:https://instagram.com/{ig}")
    if profile.get('social_vk'):
        vk = profile['social_vk']
        if not vk.startswith('http'):
            vk = f"https://vk.com/{vk}"
        vcard_lines.append(f"URL:{vk}")
    if profile.get('social_whatsapp'):
        wa = profile['social_whatsapp'].replace('+', '').replace(' ', '')
        vcard_lines.append(f"TEL;TYPE=CELL;TYPE=pref:{wa}")
    if profile.get('photo_url'):
        try:
            photo_filename = profile['photo_url'].split('/')[-1]
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    photo_data = base64.b64encode(f.read()).decode('utf-8')
                ext = photo_filename.rsplit('.', 1)[1].upper()
                if ext == 'JPG':
                    ext = 'JPEG'
                vcard_lines.append(f"PHOTO;ENCODING=b;TYPE={ext}:{photo_data}")
        except Exception as e:
            print(f"Ошибка добавления фото в vCard: {e}")
    vcard_lines.append("END:VCARD")
    return "\r\n".join(vcard_lines)

@app.route('/u/<code>')
def public_card(code):
    try:
        with open('public_card.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл public_card.html не найден", 404

@app.route('/api/public-card/<code>')
def get_public_card_data(code):
    try:
        code = code.strip().upper()
        card = get_card_by_code(code)
        if not card:
            return jsonify({'error': 'Карта не найдена'}), 404
        if card['status'] == 'free':
            return jsonify({'status': 'free', 'redirect': f'/activate?code={code}'}), 200
        if card['status'] == 'blocked':
            return jsonify({'error': 'Эта карта заблокирована'}), 403
        current_user_id = session.get('user_id')
        is_owner = current_user_id and current_user_id == card['user_id']
        if not is_owner:
            try:
                ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                user_agent = request.headers.get('User-Agent', '')
                record_visit(card['id'], ip, user_agent)
            except Exception as e:
                print(f"Ошибка записи посещения: {e}")
        profile = get_profile_by_user_id(card['user_id'])
        if not profile:
            return jsonify({'status': 'not_filled', 'card_code': code}), 200
        return jsonify({
            'status': 'ok',
            'card_code': code,
            'first_name': profile.get('first_name', ''),
            'middle_name': profile.get('middle_name') or '',
            'last_name': profile.get('last_name', ''),
            'company': profile.get('company') or '',
            'position': profile.get('position') or '',
            'phone': profile.get('phone', ''),
            'email': profile.get('email', ''),
            'photo_url': profile.get('photo_url') or '',
            'theme_preset': profile.get('theme_preset') or 'indigo',
            'bg_color': profile.get('bg_color') or '#f7fafc',
            'button_color': profile.get('button_color') or '#5a67d8',
            'bg_image_url': profile.get('bg_image_url') or '',
            'button_language': profile.get('button_language') or 'ru',
            'show_avatar': bool(profile.get('show_avatar', 1)),
            'gradient_enabled': bool(profile.get('gradient_enabled', 0)),
            'gradient_color1': profile.get('gradient_color1') or '#667eea',
            'gradient_color2': profile.get('gradient_color2') or '#764ba2',
            'gradient_direction': profile.get('gradient_direction') or '135deg',
            'social_telegram': profile.get('social_telegram') or '',
            'social_instagram': profile.get('social_instagram') or '',
            'social_whatsapp': profile.get('social_whatsapp') or '',
            'social_vk': profile.get('social_vk') or '',
            'social_max': profile.get('social_max') or ''
        }), 200
    except Exception as e:
        print(f"Ошибка показа визитки: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/u/<code>/vcard')
def download_vcard(code):
    try:
        code = code.strip().upper()
        card = get_card_by_code(code)
        if not card or card['status'] != 'activated':
            return "Карта не найдена или не активирована", 404
        profile = get_profile_by_user_id(card['user_id'])
        if not profile:
            return "Профиль не заполнен", 404
        vcard = generate_vcard(profile)
        filename = f"{profile['first_name']}_{profile['last_name']}.vcf"
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.', ' '))
        response = Response(vcard, mimetype='text/vcard', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        return response
    except Exception as e:
        print(f"Ошибка генерации vCard: {e}")
        return "Ошибка создания vCard", 500

@app.route('/card-not-filled')
def card_not_filled():
    try:
        with open('card_not_filled.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл card_not_filled.html не найден", 404

@app.route('/admin')
@admin_required
def admin_page():
    try:
        with open('admin.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл admin.html не найден", 404

@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    try:
        stats = get_admin_stats()
        return jsonify(stats), 200
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return jsonify({'error': 'Ошибка загрузки статистики'}), 500

@app.route('/api/admin/users')
@admin_required
def admin_users():
    try:
        users = get_all_users()
        for user in users:
            if user.get('created_at'):
                user['created_at'] = user['created_at'].isoformat()
            if user.get('activated_at'):
                user['activated_at'] = user['activated_at'].isoformat()
        return jsonify(users), 200
    except Exception as e:
        print(f"Ошибка получения пользователей: {e}")
        return jsonify({'error': 'Ошибка загрузки'}), 500

@app.route('/api/admin/cards')
@admin_required
def admin_cards():
    try:
        cards = get_all_cards()
        for card in cards:
            if card.get('created_at'):
                card['created_at'] = card['created_at'].isoformat()
            if card.get('activated_at'):
                card['activated_at'] = card['activated_at'].isoformat()
        return jsonify(cards), 200
    except Exception as e:
        print(f"Ошибка получения карт: {e}")
        return jsonify({'error': 'Ошибка загрузки'}), 500

@app.route('/api/admin/visits')
@admin_required
def admin_visits():
    try:
        visits = get_all_visits()
        for visit in visits:
            if visit.get('visited_at'):
                visit['visited_at'] = visit['visited_at'].isoformat()
        return jsonify(visits), 200
    except Exception as e:
        print(f"Ошибка получения посещений: {e}")
        return jsonify({'error': 'Ошибка загрузки'}), 500

@app.route('/api/admin/profiles')
@admin_required
def admin_profiles():
    try:
        profiles = get_all_profiles()
        for profile in profiles:
            if profile.get('updated_at'):
                profile['updated_at'] = profile['updated_at'].isoformat()
        return jsonify(profiles), 200
    except Exception as e:
        print(f"Ошибка получения профилей: {e}")
        return jsonify({'error': 'Ошибка загрузки'}), 500

@app.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    try:
        if session.get('user_id') == user_id:
            return jsonify({'error': 'Нельзя удалить свою учётную запись'}), 400
        result = delete_user(user_id)
        if result is not None:
            return jsonify({'message': 'Пользователь удалён'}), 200
        return jsonify({'error': 'Ошибка удаления'}), 500
    except Exception as e:
        print(f"Ошибка удаления: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/card/<int:card_id>', methods=['DELETE'])
@admin_required
def admin_delete_card(card_id):
    try:
        result = delete_card(card_id)
        if result is not None:
            return jsonify({'message': 'Карта удалена'}), 200
        return jsonify({'error': 'Ошибка удаления'}), 500
    except Exception as e:
        print(f"Ошибка удаления: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/card/<int:card_id>/unlink', methods=['POST'])
@admin_required
def admin_unlink_card(card_id):
    try:
        result = unlink_card(card_id)
        if result is not None:
            return jsonify({'message': 'Карта отвязана'}), 200
        return jsonify({'error': 'Ошибка'}), 500
    except Exception as e:
        print(f"Ошибка отвязки: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/card/<int:card_id>/status', methods=['POST'])
@admin_required
def admin_update_card_status(card_id):
    try:
        data = request.json
        new_status = data.get('status')
        if new_status not in ['free', 'activated', 'blocked']:
            return jsonify({'error': 'Недопустимый статус'}), 400
        result = update_card_status(card_id, new_status)
        if result is not None:
            return jsonify({'message': 'Статус обновлён'}), 200
        return jsonify({'error': 'Ошибка'}), 500
    except Exception as e:
        print(f"Ошибка обновления статуса: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/profile/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_profile(user_id):
    try:
        data = request.json
        required = ['first_name', 'last_name', 'phone', 'email']
        for field in required:
            if not data.get(field, '').strip():
                return jsonify({'error': f'Поле "{field}" обязательно'}), 400
        result = update_profile(user_id, data)
        if result is not None:
            return jsonify({'message': 'Профиль обновлён'}), 200
        return jsonify({'error': 'Ошибка обновления'}), 500
    except Exception as e:
        print(f"Ошибка обновления профиля: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    try:
        if session.get('user_id') == user_id:
            return jsonify({'error': 'Нельзя сбросить свой пароль через админку'}), 400
        new_password = generate_password(12)
        new_hash = generate_password_hash(new_password)
        result = reset_user_password(user_id, new_hash)
        if result is not None:
            return jsonify({'message': 'Пароль сброшен', 'new_password': new_password}), 200
        return jsonify({'error': 'Ошибка сброса'}), 500
    except Exception as e:
        print(f"Ошибка сброса пароля: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/check')
def admin_check():
    if 'user_id' not in session:
        return jsonify({'is_admin': False}), 200
    user_email = session.get('user_email', '')
    admin_emails = os.getenv('ADMIN_EMAILS', '')
    admins = [email.strip().lower() for email in admin_emails.split(',') if email.strip()]
    return jsonify({'is_admin': user_email.lower() in admins}), 200

@app.route('/api/admin/cards/add', methods=['POST'])
@admin_required
def admin_add_cards():
    try:
        data = request.json
        mode = data.get('mode', 'manual')
        if mode == 'auto':
            prefix = data.get('prefix', 'VK').strip().upper()
            count = int(data.get('count', 1))
            start_from = data.get('start_from')
            if count < 1 or count > 1000:
                return jsonify({'error': 'Количество должно быть от 1 до 1000'}), 400
            if not prefix or not all(c.isalnum() or c in '-_' for c in prefix):
                return jsonify({'error': 'Недопустимый префикс'}), 400
            codes = generate_next_codes(prefix, count, start_from)
            if len(codes) < count:
                return jsonify({'error': f'Не удалось сгенерировать {count} уникальных кодов. Свободно только {len(codes)}.'}), 400
        else:
            codes_text = data.get('codes', '')
            codes = [c.strip().upper() for c in codes_text.replace(',', '\n').split('\n') if c.strip()]
            if not codes:
                return jsonify({'error': 'Не указаны коды'}), 400
            if len(codes) > 1000:
                return jsonify({'error': 'Максимум 1000 кодов за раз'}), 400
        created, skipped, errors = create_cards_bulk(codes)
        return jsonify({'message': f'Добавлено {created} карт', 'created': created, 'skipped': skipped, 'errors': errors[:10]}), 200
    except ValueError as e:
        return jsonify({'error': 'Неверные данные'}), 400
    except Exception as e:
        print(f"Ошибка добавления карт: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/admin/cards/next-codes')
@admin_required
def admin_next_codes():
    try:
        prefix = request.args.get('prefix', 'VK').strip().upper()
        count = int(request.args.get('count', 5))
        if count < 1 or count > 20:
            count = 5
        codes = generate_next_codes(prefix, count)
        return jsonify({'codes': codes, 'prefix': prefix}), 200
    except Exception as e:
        print(f"Ошибка генерации кодов: {e}")
        return jsonify({'error': 'Ошибка'}), 500

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))