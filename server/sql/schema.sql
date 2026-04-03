CREATE DATABASE IF NOT EXISTS excellent_app DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE excellent_app;

CREATE TABLE IF NOT EXISTS teams (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    owner_user_id BIGINT NOT NULL,
    description VARCHAR(500) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_teams_owner_user_id (owner_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(64) NOT NULL,
    avatar VARCHAR(255) NULL,
    global_role VARCHAR(32) NOT NULL DEFAULT 'USER',
    business_identity VARCHAR(32) NOT NULL DEFAULT 'NORMAL_MEMBER',
    status VARCHAR(32) NOT NULL DEFAULT 'ENABLED',
    invite_code VARCHAR(32) NOT NULL,
    parent_id BIGINT NULL,
    grandparent_id BIGINT NULL,
    team_id BIGINT NULL,
    real_name VARCHAR(64) NULL,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_users_phone (phone),
    UNIQUE KEY uk_users_invite_code (invite_code),
    KEY idx_users_parent_id (parent_id),
    KEY idx_users_grandparent_id (grandparent_id),
    KEY idx_users_team_id (team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS team_members (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    team_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    team_role VARCHAR(32) NOT NULL DEFAULT 'MEMBER',
    joined_at DATETIME NOT NULL,
    UNIQUE KEY uk_team_members_team_user (team_id, user_id),
    KEY idx_team_members_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS invite_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    inviter_user_id BIGINT NOT NULL,
    invitee_user_id BIGINT NOT NULL,
    level TINYINT NOT NULL,
    invite_code VARCHAR(32) NOT NULL,
    bound_at DATETIME NOT NULL,
    KEY idx_invite_records_inviter (inviter_user_id),
    KEY idx_invite_records_invitee (invitee_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS commission_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    level1_rate DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    level2_rate DECIMAL(5,2) NOT NULL DEFAULT 2.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    updated_by BIGINT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_commissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    frozen_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    available_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    withdrawn_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY uk_user_commissions_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS packages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    package_name VARCHAR(100) NOT NULL,
    package_price DECIMAL(18,2) NOT NULL,
    package_type VARCHAR(32) NOT NULL,
    voucher_reward_rate DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    referral_voucher_rate DECIMAL(5,2) NOT NULL DEFAULT 50.00,
    ai_coupon_max_deduct_rate DECIMAL(5,2) NOT NULL DEFAULT 20.00,
    grants_product_quota INT NOT NULL DEFAULT 0,
    points_subsidy_enabled TINYINT(1) NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'ON_SHELF',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(150) NOT NULL,
    product_type VARCHAR(32) NOT NULL,
    owner_type VARCHAR(32) NOT NULL,
    owner_id BIGINT NULL,
    zone_type VARCHAR(32) NOT NULL,
    market_price DECIMAL(18,2) NULL,
    sale_price DECIMAL(18,2) NOT NULL,
    cost_price DECIMAL(18,2) NULL,
    stock INT NOT NULL DEFAULT 0,
    sold_count INT NOT NULL DEFAULT 0,
    main_image VARCHAR(255) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    requires_shipping TINYINT(1) NOT NULL DEFAULT 1,
    drop_shipping_enabled TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_products_zone_type (zone_type, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product_skus (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    sku_code VARCHAR(64) NOT NULL,
    sku_name VARCHAR(100) NOT NULL,
    sale_price DECIMAL(18,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    spec_json JSON NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ON_SHELF',
    created_at DATETIME NOT NULL,
    UNIQUE KEY uk_product_skus_sku_code (sku_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product_zone_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    zone_type VARCHAR(32) NOT NULL,
    package_required TINYINT(1) NOT NULL DEFAULT 0,
    package_id BIGINT NULL,
    repurchase_discount_rate DECIMAL(5,2) NULL,
    voucher_deduct_min_rate DECIMAL(5,2) NULL,
    voucher_deduct_max_rate DECIMAL(5,2) NULL,
    ai_coupon_reward_rate DECIMAL(5,2) NULL,
    ai_coupon_max_deduct_rate DECIMAL(5,2) NULL,
    points_purchase_enabled TINYINT(1) NOT NULL DEFAULT 0,
    balance_purchase_enabled TINYINT(1) NOT NULL DEFAULT 0,
    flash_sale_enabled TINYINT(1) NOT NULL DEFAULT 0,
    per_user_limit INT NULL,
    merchant_commission_rule_id BIGINT NULL,
    device_revenue_enabled TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_product_zone_configs_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_asset_accounts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    asset_type VARCHAR(32) NOT NULL,
    total_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    available_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    frozen_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    consumed_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    withdrawn_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY uk_user_asset_accounts_user_asset (user_id, asset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_asset_ledgers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    asset_type VARCHAR(32) NOT NULL,
    direction VARCHAR(16) NOT NULL,
    change_amount DECIMAL(18,2) NOT NULL,
    before_amount DECIMAL(18,2) NOT NULL,
    after_amount DECIMAL(18,2) NOT NULL,
    business_type VARCHAR(32) NOT NULL,
    source_id BIGINT NULL,
    source_no VARCHAR(64) NULL,
    remark VARCHAR(500) NULL,
    created_at DATETIME NOT NULL,
    KEY idx_user_asset_ledgers_user_asset (user_id, asset_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS daily_signin_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    signin_date DATE NOT NULL,
    voucher_amount DECIMAL(18,2) NOT NULL DEFAULT 100,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uk_daily_signin_user_date (user_id, signin_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NULL,
    supplier_name VARCHAR(128) NOT NULL,
    contact_name VARCHAR(64) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    qualification_desc VARCHAR(1000) NULL,
    entry_fee_amount DECIMAL(18,2) NOT NULL,
    entry_fee_paid TINYINT(1) NOT NULL DEFAULT 0,
    referral_user_id BIGINT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS supplier_entry_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    supplier_id BIGINT NOT NULL,
    order_no VARCHAR(64) NOT NULL,
    base_product_price DECIMAL(18,2) NULL,
    entry_fee_amount DECIMAL(18,2) NOT NULL,
    referral_user_id BIGINT NULL,
    referral_reward_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    paid_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uk_supplier_entry_orders_order_no (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_levels (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    level_code VARCHAR(32) NOT NULL,
    level_name VARCHAR(64) NOT NULL,
    max_product_count INT NOT NULL,
    requires_agreement TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_agent_levels_level_code (level_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_qualifications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    agent_level_id BIGINT NOT NULL,
    qualification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    product_quota INT NOT NULL,
    used_quota INT NOT NULL DEFAULT 0,
    agreement_signed TINYINT(1) NOT NULL DEFAULT 0,
    effective_at DATETIME NULL,
    expired_at DATETIME NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    team_id BIGINT NULL,
    order_type VARCHAR(32) NOT NULL,
    zone_type VARCHAR(32) NULL,
    source_ref_id BIGINT NULL,
    total_amount DECIMAL(18,2) NOT NULL,
    discount_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    payable_amount DECIMAL(18,2) NOT NULL,
    paid_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    pay_status VARCHAR(32) NOT NULL DEFAULT 'UNPAID',
    order_status VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    paid_at DATETIME NULL,
    confirmed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_orders_order_no (order_no),
    KEY idx_orders_user_id_created_at (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    sku_id BIGINT NULL,
    product_name VARCHAR(150) NOT NULL,
    sku_name VARCHAR(100) NULL,
    unit_price DECIMAL(18,2) NOT NULL,
    quantity INT NOT NULL,
    total_amount DECIMAL(18,2) NOT NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_asset_deductions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    asset_type VARCHAR(32) NOT NULL,
    deduct_amount DECIMAL(18,2) NOT NULL,
    deduct_rate DECIMAL(5,2) NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS commission_flows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    beneficiary_user_id BIGINT NOT NULL,
    source_user_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    team_id BIGINT NULL,
    level TINYINT NOT NULL,
    rate DECIMAL(5,2) NOT NULL,
    base_amount DECIMAL(18,2) NOT NULL,
    commission_amount DECIMAL(18,2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    settled_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    KEY idx_commission_flows_beneficiary (beneficiary_user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS withdraw_requests (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    team_id BIGINT NULL,
    withdraw_type VARCHAR(32) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    remark VARCHAR(500) NULL,
    reviewed_by BIGINT NULL,
    reviewed_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    KEY idx_withdraw_requests_user_id (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_addresses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    receiver_name VARCHAR(64) NOT NULL,
    receiver_phone VARCHAR(20) NOT NULL,
    province VARCHAR(64) NOT NULL,
    city VARCHAR(64) NOT NULL,
    district VARCHAR(64) NOT NULL,
    detail_address VARCHAR(255) NOT NULL,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS local_life_merchants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    owner_user_id BIGINT NULL,
    merchant_name VARCHAR(128) NOT NULL,
    category_name VARCHAR(64) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    city_code VARCHAR(20) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS merchant_stores (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    merchant_id BIGINT NOT NULL,
    store_name VARCHAR(128) NOT NULL,
    contact_phone VARCHAR(20) NULL,
    province VARCHAR(64) NULL,
    city VARCHAR(64) NULL,
    district VARCHAR(64) NULL,
    detail_address VARCHAR(255) NULL,
    latitude DECIMAL(10,6) NULL,
    longitude DECIMAL(10,6) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS local_life_services (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    merchant_id BIGINT NOT NULL,
    store_id BIGINT NULL,
    service_name VARCHAR(150) NOT NULL,
    market_price DECIMAL(18,2) NULL,
    sale_price DECIMAL(18,2) NOT NULL,
    service_type VARCHAR(32) NOT NULL,
    verification_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ON_SHELF',
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS local_life_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    merchant_id BIGINT NOT NULL,
    store_id BIGINT NULL,
    service_id BIGINT NOT NULL,
    verification_code VARCHAR(32) NULL,
    verified_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uk_local_life_orders_order_id (order_id),
    UNIQUE KEY uk_local_life_orders_verification_code (verification_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS merchant_commission_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    merchant_id BIGINT NULL,
    county_agent_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    city_agent_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    user_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    merchant_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    device_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ad_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS device_revenue_flows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_type VARCHAR(32) NOT NULL,
    business_ref_no VARCHAR(64) NOT NULL,
    beneficiary_user_id BIGINT NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    source_desc VARCHAR(255) NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ad_revenue_flows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ad_ref_no VARCHAR(64) NOT NULL,
    beneficiary_user_id BIGINT NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    source_desc VARCHAR(255) NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS package_benefits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    package_id BIGINT NOT NULL,
    benefit_type VARCHAR(32) NOT NULL,
    benefit_value VARCHAR(255) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product_qualifications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    applicant_user_id BIGINT NOT NULL,
    supplier_id BIGINT NULL,
    qualification_type VARCHAR(32) NOT NULL,
    source_ref_id BIGINT NULL,
    audit_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    audit_remark VARCHAR(500) NULL,
    audited_by BIGINT NULL,
    audited_at DATETIME NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS supplier_agreements (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    supplier_id BIGINT NOT NULL,
    agreement_type VARCHAR(32) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    signed_at DATETIME NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS supplier_referral_rewards (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    supplier_id BIGINT NOT NULL,
    referral_user_id BIGINT NOT NULL,
    entry_order_id BIGINT NOT NULL,
    reward_rate DECIMAL(5,2) NOT NULL DEFAULT 15.00,
    reward_amount DECIMAL(18,2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
