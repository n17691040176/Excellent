from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.models.commission_audit import CommissionRuleAudit
from app.models.user import User
from app.utils.helpers import iso_datetime, now


def audit_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return iso_datetime(value)
    if isinstance(value, Enum):
        return value.value
    return value


def rule_snapshot(row):
    if row is None:
        return {}
    return {column.name: audit_value(getattr(row, column.name)) for column in row.__table__.columns}


def record_rule_change(db, entity_type, entity_id, version, before, after, operator_id=None, reason=None):
    db.add(CommissionRuleAudit(entity_type=entity_type, entity_id=entity_id, rule_version=version,
                               before_values=before, after_values=after, operator_id=operator_id,
                               reason=reason, created_at=now()))


def list_rule_changes(db, entity_type, entity_id, page=1, page_size=20):
    query = db.query(CommissionRuleAudit).filter_by(entity_type=entity_type, entity_id=entity_id)
    total = query.count()
    rows = query.order_by(CommissionRuleAudit.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user.nickname for user in db.query(User).filter(User.id.in_([
        row.operator_id for row in rows if row.operator_id is not None
    ])).all()} if rows else {}
    return {'total': total, 'page': page, 'page_size': page_size, 'items': [
        {**rule_snapshot(row), 'operator_name': users.get(row.operator_id) or '系统'} for row in rows
    ]}
