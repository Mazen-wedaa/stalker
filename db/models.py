from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config.settings import DATABASE_URL
import json # Added for parsing JSON strings for lists

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    language_code = Column(String(10), default='en')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    target_accounts = relationship('TargetAccount', back_populates='user')

    def __repr__(self):
        return f'<User(telegram_id={self.telegram_id}, lang={self.language_code})>'

class TargetAccount(Base):
    __tablename__ = 'target_accounts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform = Column(String(20), nullable=False) # 'tiktok' or 'instagram'
    profile_url = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), nullable=True) # Cached username
    is_monitoring_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='target_accounts')
    snapshots = relationship('FollowerSnapshot', back_populates='target_account', order_by='FollowerSnapshot.timestamp')

    def __repr__(self):
        return f'<TargetAccount(user_id={self.user_id}, platform={self.platform}, url={self.profile_url})>'

class FollowerSnapshot(Base):
    __tablename__ = 'follower_snapshots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    followers_count = Column(Integer, nullable=False)
    following_count = Column(Integer, nullable=False)
    followers_list = Column(Text, nullable=True) # Stored as JSON string or comma-separated
    following_list = Column(Text, nullable=True) # Stored as JSON string or comma-separated

    target_account = relationship('TargetAccount', back_populates='snapshots')

    def __repr__(self):
        return f'<FollowerSnapshot(account_id={self.target_account_id}, time={self.timestamp}, followers={self.followers_count})>'

class MonitoringAccount(Base):
    __tablename__ = 'monitoring_accounts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False) # 'tiktok' or 'instagram'
    username = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False) # Consider encrypting in production
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    cookies_path = Column(String(255), nullable=True) # Path to Playwright storage_state.json
    proxy = Column(String(255), nullable=True) # Proxy assigned to this account
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MonitoringAccount(platform={self.platform}, username={self.username})>'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print('Database tables created/updated.')


