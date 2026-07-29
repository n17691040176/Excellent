from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User
from app.services.admin_rbac_service import AdminRbacService
from app.services.supplier_service import SupplierService
from app.utils.helpers import generate_code


def seed_defaults(db: Session) -> None:
    SupplierService.ensure_default_agent_levels(db)
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

    AdminRbacService.ensure_system_roles(db)
