
from sqlalchemy.orm import Session
from db.models import User, TargetAccount, FollowerSnapshot, MonitoringAccount, SessionLocal
from datetime import datetime
from typing import List, Optional

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- User Operations ---
def get_or_create_user(db: Session, telegram_id: int, language_code: str) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, language_code=language_code)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_user_language(db: Session, telegram_id: int, language_code: str) -> Optional[User]:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        user.language_code = language_code
        db.commit()
        db.refresh(user)
    return user

# --- Target Account Operations ---
def add_target_account(db: Session, user_id: int, platform: str, profile_url: str) -> TargetAccount:
    target_account = TargetAccount(user_id=user_id, platform=platform, profile_url=profile_url)
    db.add(target_account)
    db.commit()
    db.refresh(target_account)
    return target_account

def get_target_account_by_url(db: Session, profile_url: str) -> Optional[TargetAccount]:
    return db.query(TargetAccount).filter(TargetAccount.profile_url == profile_url).first()

def get_user_target_accounts(db: Session, user_id: int) -> List[TargetAccount]:
    return db.query(TargetAccount).filter(TargetAccount.user_id == user_id).all()

def get_target_account_by_id(db: Session, account_id: int) -> Optional[TargetAccount]:
    return db.query(TargetAccount).filter(TargetAccount.id == account_id).first()

def delete_target_account(db: Session, account_id: int) -> bool:
    target_account = db.query(TargetAccount).filter(TargetAccount.id == account_id).first()
    if target_account:
        db.delete(target_account)
        db.commit()
        return True
    return False

def update_target_account_status(db: Session, account_id: int, is_active: bool) -> Optional[TargetAccount]:
    target_account = db.query(TargetAccount).filter(TargetAccount.id == account_id).first()
    if target_account:
        target_account.is_monitoring_active = is_active
        db.commit()
        db.refresh(target_account)
    return target_account

def update_target_account_last_checked(db: Session, account_id: int):
    target_account = db.query(TargetAccount).filter(TargetAccount.id == account_id).first()
    if target_account:
        target_account.last_checked_at = datetime.utcnow()
        db.commit()
        db.refresh(target_account)

# --- Follower Snapshot Operations ---
def add_follower_snapshot(db: Session, target_account_id: int, followers_count: int, following_count: int, followers_list: Optional[str] = None, following_list: Optional[str] = None) -> FollowerSnapshot:
    snapshot = FollowerSnapshot(
        target_account_id=target_account_id,
        followers_count=followers_count,
        following_count=following_count,
        followers_list=followers_list,
        following_list=following_list
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot

def get_latest_snapshot(db: Session, target_account_id: int) -> Optional[FollowerSnapshot]:
    return db.query(FollowerSnapshot).filter(FollowerSnapshot.target_account_id == target_account_id).order_by(FollowerSnapshot.timestamp.desc()).first()

def get_last_two_snapshots(db: Session, target_account_id: int) -> List[FollowerSnapshot]:
    return db.query(FollowerSnapshot).filter(FollowerSnapshot.target_account_id == target_account_id).order_by(FollowerSnapshot.timestamp.desc()).limit(2).all()

# --- Monitoring Account Operations (UPDATED) ---
def add_monitoring_account(db: Session, platform: str, username: str, password: str, proxy: Optional[str] = None, cookies_path: Optional[str] = None) -> MonitoringAccount:
    mon_account = MonitoringAccount(platform=platform, username=username, password=password, proxy=proxy, cookies_path=cookies_path)
    db.add(mon_account)
    db.commit()
    db.refresh(mon_account)
    return mon_account

def get_monitoring_account(db: Session, account_id: int) -> Optional[MonitoringAccount]:
    return db.query(MonitoringAccount).filter(MonitoringAccount.id == account_id).first()

def get_all_monitoring_accounts(db: Session) -> List[MonitoringAccount]:
    return db.query(MonitoringAccount).all()

def get_available_monitoring_account(db: Session, platform: str) -> Optional[MonitoringAccount]:
    # Simple load balancing: pick the one least recently used
    return db.query(MonitoringAccount).filter(MonitoringAccount.platform == platform, MonitoringAccount.is_active == True).order_by(MonitoringAccount.last_used_at.asc()).first()

def update_monitoring_account_usage(db: Session, account_id: int, cookies_path: Optional[str] = None):
    mon_account = db.query(MonitoringAccount).filter(MonitoringAccount.id == account_id).first()
    if mon_account:
        mon_account.last_used_at = datetime.utcnow()
        if cookies_path:
            mon_account.cookies_path = cookies_path
        db.commit()
        db.refresh(mon_account)

def delete_monitoring_account(db: Session, account_id: int) -> bool:
    mon_account = db.query(MonitoringAccount).filter(MonitoringAccount.id == account_id).first()
    if mon_account:
        db.delete(mon_account)
        db.commit()
        return True
    return False


