# Файл для определения моделей

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# User
class User(db.Model, UserMixin):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    mail = db.Column(db.String(100), nullable=False)
    user_password = db.Column(db.String(255), nullable=False)
    user_role = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<USER {self.name}>'
    
    def get_id(self):
        return str(self.user_id)
    
# Torrent
class Torrent(db.Model):
    __tablename__ = "torrents"
    torrent_id = db.Column(db.Integer, primary_key=True)
    hash_str = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    

# Activity
class Activity(db.Model):
    __tablename__ = "activity"
    activity_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    torrent_id = db.Column(db.Integer, db.ForeignKey("torrents.torrent_id"))
    action_type = db.Column(db.String(100), nullable=False)

# Comment
class Comment(db.Model):
    __tablename__ = "tcomments"
    comment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    torrent_id = db.Column(db.Integer, db.ForeignKey("torrent.torrent_id"))
    comment_body = db.Column(db.String(500), nullable=False)

# ForumPost
class ForumPost(db.Model):
    __tablename__ = "forumposts"
    post_id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    post_title = db.Column(db.String(200), nullable=False)
    post_body = db.Column(db.String(1000), nullable=False)

# Moderation log
class Log(db.Model):
    __tablename__ = "logs"
    log_id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    target_id = db.Column(db.Integer, nullable=False)
    target_type = db.Column(db.String(10), nullable=False)
    action_type = db.Column(db.String(20), nullable=False) # Seed, download, upload, etc.
    action_time = db.Column(db.DateTime, nullable=False,  default=datetime.utcnow)
