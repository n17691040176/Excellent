-- 区域代理表和区域分红表
-- 执行方式: docker exec excellent-mysql mysql -uexcellent -pexcellent123 excellent_app < server/sql/region_agent_tables.sql

-- 区域代理绑定表
CREATE TABLE IF NOT EXISTS `region_agents` (
    `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT NOT NULL,
    `province` VARCHAR(64) NOT NULL DEFAULT '',
    `city` VARCHAR(64) NOT NULL DEFAULT '',
    `district` VARCHAR(64) NOT NULL DEFAULT '',
    `agent_type` ENUM('COUNTY_AGENT', 'CITY_AGENT') NOT NULL DEFAULT 'COUNTY_AGENT',
    `status` ENUM('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED') NOT NULL DEFAULT 'PENDING',
    `effective_at` DATETIME NULL,
    `expired_at` DATETIME NULL,
    `agreement_signed` TINYINT(1) NOT NULL DEFAULT 0,
    `agreement_url` VARCHAR(500) NULL,
    `audit_remark` TEXT NULL,
    `audited_by` BIGINT NULL,
    `audited_at` DATETIME NULL,
    `resource_proof_url` VARCHAR(500) NULL,
    `dividend_rate` DECIMAL(10,4) NOT NULL DEFAULT 0.0000,
    `total_orders` INT NOT NULL DEFAULT 0,
    `total_dividend` DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_region_province` (`province`),
    INDEX `idx_region_city` (`city`),
    INDEX `idx_region_district` (`district`),
    INDEX `idx_region_agent_type` (`agent_type`),
    INDEX `idx_region_status` (`status`),
    UNIQUE INDEX `idx_region_user_area` (`user_id`, `province`, `city`, `district`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 区域分红流水表
CREATE TABLE IF NOT EXISTS `region_dividend_flows` (
    `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `order_id` BIGINT NOT NULL,
    `order_no` VARCHAR(64) NOT NULL,
    `agent_id` BIGINT NOT NULL,
    `agent_user_id` BIGINT NOT NULL,
    `agent_type` VARCHAR(32) NOT NULL,
    `province` VARCHAR(64) NOT NULL,
    `city` VARCHAR(64) NOT NULL,
    `district` VARCHAR(64) NOT NULL,
    `order_amount` DECIMAL(18,2) NOT NULL,
    `dividend_rate` DECIMAL(10,4) NOT NULL,
    `dividend_amount` DECIMAL(18,2) NOT NULL,
    `status` ENUM('FROZEN', 'SETTLED', 'EXPIRED') NOT NULL DEFAULT 'FROZEN',
    `settled_at` DATETIME NULL,
    `remark` VARCHAR(255) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_dividend_order` (`order_id`),
    INDEX `idx_dividend_agent` (`agent_user_id`),
    INDEX `idx_dividend_status` (`status`),
    INDEX `idx_dividend_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
