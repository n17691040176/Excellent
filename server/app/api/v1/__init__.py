from fastapi import APIRouter

from app.api.v1 import addresses, assets, auth, commission, dashboard, local_life, orders, packages, products, suppliers, teams, users

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth.router, tags=['Auth'])
api_router.include_router(users.app_router, tags=['App Users'])
api_router.include_router(teams.app_router, tags=['App Teams'])
api_router.include_router(packages.app_router, tags=['App Packages'])
api_router.include_router(suppliers.app_router, tags=['App Suppliers'])
api_router.include_router(products.app_router, tags=['App Products'])
api_router.include_router(assets.app_router, tags=['App Assets'])
api_router.include_router(addresses.app_router, tags=['App Addresses'])
api_router.include_router(orders.app_router, tags=['App Orders'])
api_router.include_router(commission.app_router, tags=['App Commission'])
api_router.include_router(local_life.app_router, tags=['App Local Life'])
api_router.include_router(users.admin_router, tags=['Admin Users'])
api_router.include_router(dashboard.admin_router, tags=['Admin Dashboard'])
api_router.include_router(packages.admin_router, tags=['Admin Packages'])
api_router.include_router(suppliers.admin_router, tags=['Admin Suppliers'])
api_router.include_router(products.admin_router, tags=['Admin Products'])
api_router.include_router(commission.admin_router, tags=['Admin Commission'])
api_router.include_router(local_life.admin_router, tags=['Admin Local Life'])
