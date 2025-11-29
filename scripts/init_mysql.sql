-- DB 생성 (이미 만들어져 있으면 에러 없이 넘어감)
CREATE DATABASE IF NOT EXISTS erp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE erp;

-- employees 테이블 생성
CREATE TABLE IF NOT EXISTS employees (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  department VARCHAR(100) NOT NULL,
  position VARCHAR(100) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    employee_id BIGINT NOT NULL,
    attendance_date DATE NOT NULL,
    check_in DATETIME NOT NULL,
    check_out DATETIME NULL,
    work_minutes INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attendance_employee
        FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS leave_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    employee_id BIGINT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days INT NOT NULL,
    leave_type VARCHAR(20) NOT NULL,   -- annual, sick, etc
    status VARCHAR(20) NOT NULL,       -- requested, approved, rejected
    reason VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_leave_employee
        FOREIGN KEY (employee_id) REFERENCES employees(id)
);

