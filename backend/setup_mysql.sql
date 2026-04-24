-- ============================================================
-- setup_mysql.sql — Anchor Cloud Database Bootstrap
--
-- Run this ONCE as MySQL root to create the database and user.
-- Then the Python app (SQLAlchemy) will create the tables.
--
-- Usage:
--   mysql -u root -p < setup_mysql.sql
-- ============================================================

-- Create database
CREATE DATABASE IF NOT EXISTS anchor_cloud
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Create dedicated user (replace passwords below!)
CREATE USER IF NOT EXISTS 'anchor_user'@'localhost'
  IDENTIFIED BY 'CHANGE_ME_strong_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON anchor_cloud.* TO 'anchor_user'@'localhost';

-- Apply
FLUSH PRIVILEGES;

-- Confirm
SELECT 'Anchor Cloud database and user created successfully.' AS status;
SHOW DATABASES LIKE 'anchor_cloud';