from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.commission_service import CommissionService


@celery_app.task(name='settle_commission_for_order')
def settle_commission_for_order(order_id: int) -> bool:
    db = SessionLocal()
    try:
        CommissionService.settle_for_order(db, order_id)
        return True
    finally:
        db.close()
