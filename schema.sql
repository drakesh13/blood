-- Minimal schema for Rakth Sathi (subset)

CREATE DATABASE IF NOT EXISTS rakth_sathi CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE rakth_sathi;

-- users table for auth
CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- donors (simplified)
CREATE TABLE IF NOT EXISTS donors (
  donor_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  contact_number VARCHAR(20) DEFAULT NULL,
  city VARCHAR(100) DEFAULT NULL,
  state VARCHAR(50) DEFAULT NULL,
  blood_group ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') DEFAULT NULL,
  availability ENUM('Yes','No') DEFAULT NULL,
  months_since_first_donation INT DEFAULT NULL,
  number_of_donation INT DEFAULT NULL,
  pints_donated INT DEFAULT NULL,
  created_at DATE DEFAULT NULL,
  UNIQUE KEY (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- requests
CREATE TABLE IF NOT EXISTS requests (
  request_id INT AUTO_INCREMENT PRIMARY KEY,
  recipient_id INT DEFAULT NULL,
  blood_group_needed ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') DEFAULT NULL,
  urgency ENUM('Low','Medium','High','Critical') DEFAULT NULL,
  city VARCHAR(100) DEFAULT NULL,
  state VARCHAR(50) DEFAULT NULL,
  status ENUM('Open','Matched','Closed') DEFAULT 'Open',
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- matches
CREATE TABLE IF NOT EXISTS matches (
  match_id INT AUTO_INCREMENT PRIMARY KEY,
  request_id INT DEFAULT NULL,
  donor_id INT DEFAULT NULL,
  match_score FLOAT DEFAULT NULL,
  status ENUM('Pending','Accepted','Rejected','Completed') DEFAULT 'Pending',
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
