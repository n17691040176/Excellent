from fastapi import APIRouter

from app.api.v1 import (
    addresses,
    admin_commerce,
    admin_invites,
    admin_permissions,
    admin_rbac,
    admin_region_agents,
    assets,
    auth,
    commerce,
    commission,
    dashboard,
    earning_rules,
    local_life,
    orders,
    packages,
    page_decorations,
    payments,
    products,
    suppliers,
    teams,
    users,
)

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth.router, tags=['Auth'])
api_router.include_router(users.app_router, tags=['App Users'])
api_router.include_router(teams.app_router, tags=['App Teams'])
api_router.include_router(packages.app_router, tags=['App Packages'])
api_router.include_router(suppliers.app_router, tags=['App Suppliers'])
api_router.include_router(products.app_router, tags=['App Products'])
api_router.include_router(commerce.app_router, tags=['App Commerce'])
api_router.include_router(assets.app_router, tags=['App Assets'])
api_router.include_router(addresses.app_router, tags=['App Addresses'])
api_router.include_router(orders.app_router, tags=['App Orders'])
api_router.include_router(payments.app_router, tags=['App Payments'])
api_router.include_router(commission.app_router, tags=['App Commission'])
api_router.include_router(local_life.app_router, tags=['App Local Life'])
api_router.include_router(page_decorations.app_router, tags=['App Page Decorations'])
api_router.include_router(users.admin_router, tags=['Admin Users'])
api_router.include_router(dashboard.admin_router, tags=['Admin Dashboard'])
api_router.include_router(packages.admin_router, tags=['Admin Packages'])
api_router.include_router(suppliers.admin_router, tags=['Admin Suppliers'])
api_router.include_router(products.admin_router, tags=['Admin Products'])
api_router.include_router(orders.admin_router, tags=['Admin Orders'])
api_router.include_router(payments.admin_router, tags=['Admin Payments'])
api_router.include_router(commission.admin_router, tags=['Admin Commission'])
api_router.include_router(earning_rules.admin_router, tags=['Admin Earning Rules'])
api_router.include_router(admin_region_agents.router, tags=['Admin Region Agents'])
api_router.include_router(admin_invites.admin_router, tags=['Admin Invites'])
api_router.include_router(admin_commerce.admin_router, tags=['Admin Commerce'])
api_router.include_router(admin_permissions.router, tags=['Admin Permissions'])
api_router.include_router(admin_rbac.router, tags=['Admin RBAC'])
api_router.include_router(local_life.admin_router, tags=['Admin Local Life'])
api_router.include_router(page_decorations.admin_router, tags=['Admin Page Decorations'])
