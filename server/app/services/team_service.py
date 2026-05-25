from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import GlobalRole, TeamRole, TeamStatus
from app.models.team import Team, TeamMember
from app.models.user import User
from app.utils.helpers import now


class TeamService:
    @staticmethod
    def create_team(db: Session, current_user: User, name: str, description: str | None) -> Team:
        if current_user.team_id:
            raise ConflictError('User already joined a team')
        team = Team(name=name, description=description, owner_user_id=current_user.id, status=TeamStatus.ACTIVE)
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=current_user.id, team_role=TeamRole.OWNER, joined_at=now()))
        current_user.team_id = team.id
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def get_current_team(db: Session, current_user: User) -> Team | None:
        if not current_user.team_id:
            return None
        return db.get(Team, current_user.team_id)

    @staticmethod
    def update_team(db: Session, current_user: User, team_id: int, name: str | None, description: str | None) -> Team:
        team = db.get(Team, team_id)
        if not team:
            raise NotFoundError('Team not found')
        if current_user.id != team.owner_user_id and current_user.global_role != GlobalRole.SUPER_ADMIN:
            raise ForbiddenError('Only owner can update team')
        if name:
            team.name = name
        if description is not None:
            team.description = description
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def dissolve_team(db: Session, current_user: User, team_id: int) -> None:
        team = db.get(Team, team_id)
        if not team:
            raise NotFoundError('Team not found')
        if current_user.id != team.owner_user_id and current_user.global_role != GlobalRole.SUPER_ADMIN:
            raise ForbiddenError('Only owner can dissolve team')
        team.status = TeamStatus.DISBANDED
        members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
        user_ids = [member.user_id for member in members]
        db.query(User).filter(User.id.in_(user_ids)).update({User.team_id: None}, synchronize_session=False)
        db.commit()

    @staticmethod
    def list_members(db: Session, team_id: int) -> list[TeamMember]:
        return db.query(TeamMember).filter(TeamMember.team_id == team_id).all()

    @staticmethod
    def join_team(db: Session, current_user: User, team_id: int) -> None:
        if current_user.team_id:
            raise ConflictError('User already joined a team')
        team = db.get(Team, team_id)
        if not team or team.status != TeamStatus.ACTIVE:
            raise NotFoundError('Active team not found')
        db.add(TeamMember(team_id=team_id, user_id=current_user.id, team_role=TeamRole.MEMBER, joined_at=now()))
        current_user.team_id = team_id
        db.commit()

    @staticmethod
    def update_member_role(db: Session, current_user: User, team_id: int, user_id: int, team_role: TeamRole) -> None:
        team = db.get(Team, team_id)
        if not team:
            raise NotFoundError('Team not found')
        if current_user.id != team.owner_user_id and current_user.global_role != GlobalRole.SUPER_ADMIN:
            raise ForbiddenError('Only owner can update role')
        member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
        if not member:
            raise NotFoundError('Member not found')
        member.team_role = team_role
        db.commit()

    @staticmethod
    def remove_member(db: Session, current_user: User, team_id: int, user_id: int) -> None:
        team = db.get(Team, team_id)
        if not team:
            raise NotFoundError('Team not found')
        if current_user.id != team.owner_user_id and current_user.global_role != GlobalRole.SUPER_ADMIN:
            raise ForbiddenError('Only owner can remove member')
        member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
        if not member:
            raise NotFoundError('Member not found')
        db.delete(member)
        db.query(User).filter(User.id == user_id).update({User.team_id: None})
        db.commit()
