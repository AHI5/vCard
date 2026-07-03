import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def init_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS nfc_cards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE nfc_cards")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        connection.commit()
        cursor.close()
        connection.close()
        print("База данных успешно создана!")
        return True
    except mysql.connector.Error as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == '__main__':
    init_database()