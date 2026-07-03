import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'nfc_cards'),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except Error as e:
        print(f"Ошибка подключения к БД: {e}")
        return None

def execute_query(query, params=None, fetch=False):
    connection = get_db_connection()
    if not connection:
        return None
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            connection.commit()
            if cursor.lastrowid and cursor.lastrowid > 0:
                result = cursor.lastrowid
            else:
                result = cursor.rowcount
        cursor.close()
        connection.close()
        return result
    except Error as e:
        print(f"Ошибка выполнения запроса: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        return None
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

def get_user_by_email(email):
    query = "SELECT * FROM users WHERE email = %s"
    result = execute_query(query, (email,), fetch=True)
    return result[0] if result else None

def get_user_by_id(user_id):
    query = "SELECT * FROM users WHERE id = %s"
    result = execute_query(query, (user_id,), fetch=True)
    return result[0] if result else None

def create_user(email, password_hash):
    query = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
    return execute_query(query, (email, password_hash))

def get_card_by_code(activation_code):
    query = "SELECT * FROM cards WHERE activation_code = %s"
    result = execute_query(query, (activation_code,), fetch=True)
    return result[0] if result else None

def activate_card(activation_code, user_id):
    query = "UPDATE cards SET user_id = %s, status = 'activated', activated_at = NOW() WHERE activation_code = %s AND status = 'free'"
    return execute_query(query, (user_id, activation_code))

def get_profile_by_user_id(user_id):
    query = "SELECT * FROM profiles WHERE user_id = %s"
    result = execute_query(query, (user_id,), fetch=True)
    return result[0] if result else None

def create_or_update_profile(user_id, profile_data):
    query = """
        INSERT INTO profiles (
            user_id, first_name, middle_name, last_name, company, position, 
            phone, email, photo_url,
            theme_preset, bg_color, button_color, bg_image_url,
            button_language, show_avatar, gradient_enabled,
            gradient_color1, gradient_color2, gradient_direction,
            social_telegram, social_instagram, social_whatsapp, social_vk, social_max
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            first_name = VALUES(first_name),
            middle_name = VALUES(middle_name),
            last_name = VALUES(last_name),
            company = VALUES(company),
            position = VALUES(position),
            phone = VALUES(phone),
            email = VALUES(email),
            photo_url = VALUES(photo_url),
            theme_preset = VALUES(theme_preset),
            bg_color = VALUES(bg_color),
            button_color = VALUES(button_color),
            bg_image_url = VALUES(bg_image_url),
            button_language = VALUES(button_language),
            show_avatar = VALUES(show_avatar),
            gradient_enabled = VALUES(gradient_enabled),
            gradient_color1 = VALUES(gradient_color1),
            gradient_color2 = VALUES(gradient_color2),
            gradient_direction = VALUES(gradient_direction),
            social_telegram = VALUES(social_telegram),
            social_instagram = VALUES(social_instagram),
            social_whatsapp = VALUES(social_whatsapp),
            social_vk = VALUES(social_vk),
            social_max = VALUES(social_max)
    """
    params = (
        user_id,
        profile_data.get('first_name'),
        profile_data.get('middle_name'),
        profile_data.get('last_name'),
        profile_data.get('company'),
        profile_data.get('position'),
        profile_data.get('phone'),
        profile_data.get('email'),
        profile_data.get('photo_url'),
        profile_data.get('theme_preset', 'indigo'),
        profile_data.get('bg_color', '#f7fafc'),
        profile_data.get('button_color', '#5a67d8'),
        profile_data.get('bg_image_url'),
        profile_data.get('button_language', 'ru'),
        1 if profile_data.get('show_avatar', True) else 0,
        1 if profile_data.get('gradient_enabled', False) else 0,
        profile_data.get('gradient_color1', '#667eea'),
        profile_data.get('gradient_color2', '#764ba2'),
        profile_data.get('gradient_direction', '135deg'),
        profile_data.get('social_telegram'),
        profile_data.get('social_instagram'),
        profile_data.get('social_whatsapp'),
        profile_data.get('social_vk'),
        profile_data.get('social_max')
    )
    return execute_query(query, params)

def record_visit(card_id, ip, user_agent):
    query = "INSERT INTO visits (card_id, ip, user_agent) VALUES (%s, %s, %s)"
    return execute_query(query, (card_id, ip, user_agent))

def get_visit_stats(card_id):
    query = "SELECT COUNT(*) as total_visits, MAX(visited_at) as last_visit FROM visits WHERE card_id = %s"
    result = execute_query(query, (card_id,), fetch=True)
    return result[0] if result else None

def get_card_by_user_id(user_id):
    query = "SELECT * FROM cards WHERE user_id = %s"
    result = execute_query(query, (user_id,), fetch=True)
    return result[0] if result else None

def get_visit_stats_by_user_id(user_id):
    query = "SELECT COUNT(v.id) as total_visits, MAX(v.visited_at) as last_visit FROM visits v JOIN cards c ON v.card_id = c.id WHERE c.user_id = %s"
    result = execute_query(query, (user_id,), fetch=True)
    return result[0] if result else {'total_visits': 0, 'last_visit': None}

def create_password_reset_token(user_id, token, expires_at):
    query = "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"
    return execute_query(query, (user_id, token, expires_at))

def get_valid_reset_token(token):
    query = "SELECT * FROM password_reset_tokens WHERE token = %s AND used = FALSE AND expires_at > NOW()"
    result = execute_query(query, (token,), fetch=True)
    return result[0] if result else None

def mark_token_as_used(token):
    query = "UPDATE password_reset_tokens SET used = TRUE WHERE token = %s"
    return execute_query(query, (token,))

def update_user_password(user_id, password_hash):
    query = "UPDATE users SET password_hash = %s WHERE id = %s"
    return execute_query(query, (password_hash, user_id))

# ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ

def get_all_users():
    query = "SELECT u.id, u.email, u.created_at, c.activation_code, c.status, c.activated_at FROM users u LEFT JOIN cards c ON u.id = c.user_id ORDER BY u.created_at DESC"
    result = execute_query(query, fetch=True)
    return result or []

def get_all_cards():
    query = "SELECT c.id, c.activation_code, c.status, c.activated_at, c.created_at, u.id as user_id, u.email FROM cards c LEFT JOIN users u ON c.user_id = u.id ORDER BY c.created_at DESC"
    result = execute_query(query, fetch=True)
    return result or []

def get_all_visits():
    query = "SELECT v.id, v.visited_at, v.ip, v.user_agent, c.activation_code, u.email FROM visits v JOIN cards c ON v.card_id = c.id LEFT JOIN users u ON c.user_id = u.id ORDER BY v.visited_at DESC LIMIT 1000"
    result = execute_query(query, fetch=True)
    return result or []

def get_all_profiles():
    query = "SELECT p.*, u.email as user_email FROM profiles p JOIN users u ON p.user_id = u.id ORDER BY p.updated_at DESC"
    result = execute_query(query, fetch=True)
    return result or []

def get_admin_stats():
    queries = {
        'total_users': "SELECT COUNT(*) as count FROM users",
        'total_cards': "SELECT COUNT(*) as count FROM cards",
        'free_cards': "SELECT COUNT(*) as count FROM cards WHERE status = 'free'",
        'activated_cards': "SELECT COUNT(*) as count FROM cards WHERE status = 'activated'",
        'total_visits': "SELECT COUNT(*) as count FROM visits",
        'total_profiles': "SELECT COUNT(*) as count FROM profiles"
    }
    stats = {}
    for key, query in queries.items():
        result = execute_query(query, fetch=True)
        stats[key] = result[0]['count'] if result else 0
    return stats

def delete_user(user_id):
    query = "DELETE FROM users WHERE id = %s"
    return execute_query(query, (user_id,))

def delete_card(card_id):
    query = "DELETE FROM cards WHERE id = %s"
    return execute_query(query, (card_id,))

def update_card_status(card_id, new_status):
    query = "UPDATE cards SET status = %s WHERE id = %s"
    return execute_query(query, (new_status, card_id))

def unlink_card(card_id):
    query = "UPDATE cards SET user_id = NULL, status = 'free', activated_at = NULL WHERE id = %s"
    return execute_query(query, (card_id,))

def update_profile(user_id, profile_data):
    query = """
        UPDATE profiles SET
            first_name = %s, last_name = %s, company = %s, position = %s,
            phone = %s, email = %s, social_telegram = %s, social_instagram = %s,
            social_whatsapp = %s, social_vk = %s, social_max = %s
        WHERE user_id = %s
    """
    params = (
        profile_data.get('first_name'),
        profile_data.get('last_name'),
        profile_data.get('company') or None,
        profile_data.get('position') or None,
        profile_data.get('phone'),
        profile_data.get('email'),
        profile_data.get('social_telegram') or None,
        profile_data.get('social_instagram') or None,
        profile_data.get('social_whatsapp') or None,
        profile_data.get('social_vk') or None,
        profile_data.get('social_max') or None,
        user_id
    )
    return execute_query(query, params)

def reset_user_password(user_id, new_password_hash):
    query = "UPDATE users SET password_hash = %s WHERE id = %s"
    return execute_query(query, (new_password_hash, user_id))

# ФУНКЦИИ ДОБАВЛЕНИЯ КАРТ

def create_card(activation_code):
    query = "INSERT INTO cards (activation_code, status) VALUES (%s, 'free')"
    return execute_query(query, (activation_code,))

def create_cards_bulk(codes):
    created = 0
    skipped = 0
    errors = []
    for code in codes:
        code = code.strip().upper()
        if not code:
            continue
        if not all(c.isalnum() or c in '-_' for c in code):
            errors.append(f'{code}: недопустимые символы')
            continue
        existing = get_card_by_code(code)
        if existing:
            skipped += 1
            continue
        try:
            result = create_card(code)
            if result:
                created += 1
            else:
                errors.append(f'{code}: ошибка создания')
        except Exception as e:
            errors.append(f'{code}: {str(e)}')
    return created, skipped, errors

def generate_next_codes(prefix='VK', count=1, start_from=None):
    if start_from is None:
        query = "SELECT activation_code FROM cards WHERE activation_code LIKE %s ORDER BY id DESC LIMIT 1"
        result = execute_query(query, (f'{prefix}-%',), fetch=True)
        if result and result[0]['activation_code']:
            last_code = result[0]['activation_code']
            try:
                last_num = int(last_code.split('-')[-1])
                start_from = last_num + 1
            except:
                start_from = 1
        else:
            start_from = 1
    codes = []
    current = start_from
    while len(codes) < count:
        code = f"{prefix}-{current:03d}"
        if not get_card_by_code(code):
            codes.append(code)
        current += 1
        if current > 99999:
            break
    return codes