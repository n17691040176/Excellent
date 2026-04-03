from sqlalchemy.orm import Session

from app.models.commission import CommissionConfig
from app.models.enums import GlobalRole, UserStatus
from app.models.supplier import AgentLevel
from app.models.user import User
from app.services.supplier_service import SupplierService
from app.utils.helpers import generate_code, now
from app.core.security import hash_password


def seed_defaults(db: Session) -> None:
    SupplierService.ensure_default_agent_levels(db)
    if not db.query(CommissionConfig).filter(CommissionConfig.is_active.is_(True)).first():
        db.add(CommissionConfig(level1_rate=5, level2_rate=2, is_active=True, updated_at=now()))
        db.commit()

    admin = db.query(User).filter(User.phone == '18800000000').first()
    if not admin:
        db.add(
            User(
                phone='18800000000',
                password_hash=hash_password('Admin@123'),
                nickname='超级管理员',
                global_role=GlobalRole.SUPER_ADMIN,
                status=UserStatus.ENABLED,
                invite_code=generate_code(length=8),
            )
        )
        db.commit()
