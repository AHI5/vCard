CREATE DATABASE IF NOT EXISTS nfc_cards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nfc_cards;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    activation_code VARCHAR(20) UNIQUE NOT NULL,
    user_id INT DEFAULT NULL,
    status ENUM('free', 'activated', 'blocked') DEFAULT 'free',
    activated_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_activation_code (activation_code),
    INDEX idx_status (status),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    company VARCHAR(255),
    position VARCHAR(255),
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    photo_url VARCHAR(500),
    theme_preset VARCHAR(50) DEFAULT 'indigo',
    bg_color VARCHAR(20) DEFAULT '#f7fafc',
    button_color VARCHAR(20) DEFAULT '#5a67d8',
    bg_image_url VARCHAR(500) DEFAULT NULL,
    button_language ENUM('ru', 'en') DEFAULT 'ru',
    show_avatar TINYINT(1) DEFAULT 1,
    gradient_enabled TINYINT(1) DEFAULT 0,
    gradient_color1 VARCHAR(20) DEFAULT '#667eea',
    gradient_color2 VARCHAR(20) DEFAULT '#764ba2',
    gradient_direction VARCHAR(20) DEFAULT '135deg',
    social_telegram VARCHAR(255),
    social_instagram VARCHAR(255),
    social_whatsapp VARCHAR(50),
    social_vk VARCHAR(255),
    social_max VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    card_id INT NOT NULL,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    INDEX idx_card_id (card_id),
    INDEX idx_visited_at (visited_at),
    INDEX idx_card_visited (card_id, visited_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token (token),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO cards (activation_code, status) VALUES 
('VK-001', 'free'),
('VK-002', 'free'),
('VK-003', 'free');