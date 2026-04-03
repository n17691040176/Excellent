from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.enums import TeamRole
from app.models.user import User
from app.schemas.team import TeamCreateRequest, TeamRoleUpdateRequest, TeamUpdateRequest
from app.services.team_service import TeamService

app_router = APIRouter(prefix='/app/teams')


@app_router.post('')
def create_team(payload: TeamCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    team = TeamService.create_team(db, current_user, payload.name, payload.description)
    return {'code': 0, 'message': 'success', 'data': team}


@app_router.get('/current')
def current_team(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': TeamService.get_current_team(db, current_user)}


@app_router.put('/{team_id}')
def update_team(team_id: int, payload: TeamUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    team = TeamService.update_team(db, current_user, team_id, payload.name, payload.description)
    return {'code': 0, 'message': 'success', 'data': team}


@app_router.delete('/{team_id}')
def dissolve_team(team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    TeamService.dissolve_team(db, current_user, team_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.get('/{team_id}/members')
def members(team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': TeamService.list_members(db, team_id)}


@app_router.post('/{team_id}/join')
def join(team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    TeamService.join_team(db, current_user, team_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.patch('/{team_id}/members/{user_id}/role')
def update_role(
    team_id: int,
    user_id: int,
    payload: TeamRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    TeamService.update_member_role(db, current_user, team_id, user_id, TeamRole(payload.team_role))
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.delete('/{team_id}/members/{user_id}')
def remove_member(team_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    TeamService.remove_member(db, current_user, team_id, user_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}
