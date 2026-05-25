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
    phone VARCHAR(20) NULL,
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

CREATE TABLE IF NOT EXISTS user_legacy_profiles (
    user_id BIGINT PRIMARY KEY,
    legacy_user_id BIGINT NOT NULL,
    dept_id BIGINT NULL,
    user_name VARCHAR(64) NULL,
    nick_name VARCHAR(255) NULL,
    user_type VARCHAR(32) NULL,
    email VARCHAR(128) NULL,
    phonenumber VARCHAR(20) NULL,
    signature TEXT NULL,
    sex VARCHAR(8) NULL,
    avatar VARCHAR(255) NULL,
    password VARCHAR(255) NULL,
    pay_password VARCHAR(255) NULL,
    status VARCHAR(32) NULL,
    del_flag VARCHAR(32) NULL,
    login_ip VARCHAR(128) NULL,
    login_date DATETIME NULL,
    create_by VARCHAR(64) NULL,
    create_time DATETIME NULL,
    update_by VARCHAR(64) NULL,
    update_time DATETIME NULL,
    remark TEXT NULL,
    superior BIGINT NULL,
    open_id VARCHAR(128) NULL,
    union_id VARCHAR(128) NULL,
    applet_qr_code VARCHAR(255) NULL,
    app_qr_code VARCHAR(255) NULL,
    invite_code VARCHAR(32) NULL,
    wx_qr_code VARCHAR(255) NULL,
    zfb_qr_code VARCHAR(255) NULL,
    zfb_nick_name VARCHAR(128) NULL,
    zfb_avatar VARCHAR(255) NULL,
    zfb_open_id VARCHAR(128) NULL,
    zfb_user_id VARCHAR(128) NULL,
    store_zfb_nick_name VARCHAR(128) NULL,
    store_zfb_avatar VARCHAR(255) NULL,
    store_zfb_open_id VARCHAR(128) NULL,
    divide_num INT NULL,
    activate INT NULL,
    partner INT NULL,
    sheng_withdraw INT NULL,
    imported_at DATETIME NOT NULL,
    UNIQUE KEY uk_user_legacy_profiles_legacy_user_id (legacy_user_id),
    CONSTRAINT fk_user_legacy_profiles_user FOREIGN KEY (user_id) REFERENCES users(id)
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

CREATE TABLE IF NOT EXISTS earning_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_code VARCHAR(64) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    rule_type VARCHAR(32) NOT NULL,
    product_id BIGINT NULL,
    member_level VARCHAR(32) NULL,
    commission_level INT NULL,
    subject_type VARCHAR(32) NOT NULL DEFAULT 'USER',
    trigger_event VARCHAR(64) NOT NULL,
    calculation_basis VARCHAR(128) NOT NULL,
    calculation_method VARCHAR(32) NOT NULL,
    reward_rate DECIMAL(7,4) NOT NULL DEFAULT 0,
    reward_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    cap_amount DECIMAL(18,2) NULL,
    min_condition VARCHAR(255) NULL,
    qualification_level VARCHAR(64) NULL,
    settlement_cycle VARCHAR(32) NOT NULL DEFAULT 'MONTHLY',
    settlement_delay_days INT NOT NULL DEFAULT 0,
    freeze_days INT NOT NULL DEFAULT 0,
    priority INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    compliance_note TEXT NULL,
    remark VARCHAR(500) NULL,
    valid_from DATETIME NULL,
    valid_to DATETIME NULL,
    created_by BIGINT NULL,
    updated_by BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_earning_rules_rule_code (rule_code),
    KEY idx_earning_rules_rule_code (rule_code),
    KEY idx_earning_rules_rule_type (rule_type),
    KEY idx_earning_rules_product_id (product_id),
    KEY idx_earning_rules_member_level (member_level),
    KEY idx_earning_rules_commission_level (commission_level)
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
    points_only_enabled TINYINT(1) NOT NULL DEFAULT 0,
    points_cash_enabled TINYINT(1) NOT NULL DEFAULT 1,
    cash_only_enabled TINYINT(1) NOT NULL DEFAULT 1,
    balance_only_enabled TINYINT(1) NOT NULL DEFAULT 1,
    balance_points_enabled TINYINT(1) NOT NULL DEFAULT 1,
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

CREATE TABLE IF NOT EXISTS user_power_banks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    device_code VARCHAR(64) NOT NULL,
    device_name VARCHAR(128) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    bound_at DATETIME NOT NULL,
    last_income_date DATE NULL,
    total_income_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_referral_income_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    remark VARCHAR(255) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY uk_user_power_banks_device_code (device_code),
    KEY idx_user_power_banks_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_power_bank_income_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    power_bank_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    referrer_user_id BIGINT NULL,
    income_date DATE NOT NULL,
    owner_income_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    referrer_income_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uk_power_bank_income_date (power_bank_id, income_date),
    KEY idx_power_bank_income_records_power_bank_id (power_bank_id),
    KEY idx_power_bank_income_records_user_id (user_id)
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
    total_price DECIMAL(18,2) NULL,
    pay_price DECIMAL(18,2) NULL,
    create_time DATETIME NULL,
    create_by BIGINT NULL,
    update_by BIGINT NULL,
    update_time DATETIME NULL,
    address_id BIGINT NULL,
    is_delete INT NULL,
    state INT NULL,
    bank_card_id BIGINT NULL,
    pay_time DATETIME NULL,
    pay_way INT NULL,
    trade_no VARCHAR(128) NULL,
    remark TEXT NULL,
    dept_id BIGINT NULL,
    write_off_qr_code VARCHAR(255) NULL,
    legacy_order_type INT NULL,
    is_seperate INT NULL,
    xiaofeijin_price DECIMAL(18,2) NULL,
    logistics_name VARCHAR(128) NULL,
    logistics_no VARCHAR(128) NULL,
    evaluate INT NULL,
    refund_state INT NULL,
    refund_no VARCHAR(128) NULL,
    refund_time DATETIME NULL,
    refund_price DECIMAL(18,2) NULL,
    refund_remark TEXT NULL,
    refund_real_price DECIMAL(18,2) NULL,
    refund_trade_no VARCHAR(128) NULL,
    refund_by BIGINT NULL,
    refund_verify_state INT NULL,
    refund_verify_time DATETIME NULL,
    writeoff_by BIGINT NULL,
    writeoff_time DATETIME NULL,
    is_send INT NULL,
    order_by BIGINT NULL,
    is_bonus INT NULL,
    bonus_amount DECIMAL(18,2) NULL,
    re_order_by_reason VARCHAR(255) NULL,
    is_re_order_by INT NULL,
    legacy_imported_at DATETIME NULL,
    legacy_source_file VARCHAR(255) NULL,
    UNIQUE KEY uk_orders_order_no (order_no),
    KEY idx_orders_user_id_created_at (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payment_transactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    order_no VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    amount DECIMAL(18,2) NOT NULL,
    out_trade_no VARCHAR(128) NOT NULL,
    provider_trade_no VARCHAR(128) NULL,
    provider_app_id VARCHAR(64) NULL,
    provider_payload JSON NULL,
    request_payload JSON NULL,
    notify_payload JSON NULL,
    paid_at DATETIME NULL,
    failed_reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_payment_transactions_out_trade_no (out_trade_no),
    KEY idx_payment_transactions_order_id (order_id),
    KEY idx_payment_transactions_order_no (order_no),
    KEY idx_payment_transactions_channel (channel),
    KEY idx_payment_transactions_status (status)
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

CREATE TABLE IF NOT EXISTS user_favorite_products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_favorite_products_user_product (user_id, product_id),
    KEY idx_user_favorite_products_user_id (user_id),
    KEY idx_user_favorite_products_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_product_footprints (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    view_count INT NOT NULL DEFAULT 1,
    last_viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_product_footprints_user_product (user_id, product_id),
    KEY idx_user_product_footprints_user_id (user_id),
    KEY idx_user_product_footprints_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS shopping_cart_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    sku_id BIGINT NULL,
    quantity INT NOT NULL DEFAULT 1,
    selected TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_shopping_cart_items_user_product (user_id, product_id),
    KEY idx_shopping_cart_items_user_id (user_id),
    KEY idx_shopping_cart_items_product_id (product_id)
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
