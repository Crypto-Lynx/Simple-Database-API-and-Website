# Файл для определения моделей

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# User
class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<USER {self.name}>'
    
    def get_id(self):
        return str(self.user_id)
    
# Torrent
class Torrent(db.Model):
    __tablename__ = "torrent"
    torrent_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_hash = db.Column(db.String(255), nullable=False)

# Activity
class Activity(db.Model):
    __tablename__ = "activity"
    activity_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    torrent_id = db.Column(db.Integer, db.ForeignKey("torrent.torrent_id"))
    action_type = db.Column(db.String(30), nullable=False)

# Comment
class Comment(db.Model):
    __tablename__ = "comment"
    comment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    torrent_id = db.Column(db.Integer, db.ForeignKey("torrent.torrent_id"))
    content = db.Column(db.String(500), nullable=False)

# ForumPost
class ForumPost(db.Model):
    __tablename__ = "forumpost"
    post_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(1000), nullable=False)

# Moderation log
class ModerationLog(db.Model):
    __tablename__ = "moderationlog"
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    action_type = db.Column(db.String(200), nullable=False) # Seed, download, upload, etc.
    time = db.Column(db.DateTime, nullable=False,  default=datetime.utcnow)


# UserRole
class UserRole(db.Model):
    __tablename__ = "userrole"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), nullable=False)
    permissions = db.Column(db.String(100), nullable=False)


# Supportive role assignment table
class UserRoleAssignment(db.Model):
    pass
    __tablename__ = "userroleassignment"
    assignment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("userrole.role_id"), nullable=False)