-- Application startup applies these changes conditionally. For manual migration,
-- execute each ALTER only if its column/type change has not already been applied.
-- Existing raw amounts cannot be recovered; retain precision_known = 0.
ALTER TABLE city_partner_seats ADD COLUMN rule_version VARCHAR(64) NOT NULL DEFAULT 'city-partner-v1';
ALTER TABLE city_partner_commission_flows ADD COLUMN calculation_precision_known TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE city_partner_commission_flows MODIFY COLUMN calculated_amount DECIMAL(48,26) NOT NULL;

CREATE TABLE IF NOT EXISTS commission_rule_audits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entity_type VARCHAR(32) NOT NULL,
    entity_id BIGINT NOT NULL,
    rule_version VARCHAR(64) NOT NULL,
    before_values JSON NOT NULL,
    after_values JSON NOT NULL,
    operator_id BIGINT NULL,
    reason VARCHAR(500) NULL,
    created_at DATETIME NOT NULL,
    KEY ix_commission_rule_audits_entity (entity_type, entity_id, id),
    FOREIGN KEY (operator_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
