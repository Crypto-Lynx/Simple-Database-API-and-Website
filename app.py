from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

# Модели
from models import db, User, Torrent, Activity, Comment, ForumPost, Log

# Нсатройки приложения
app = Flask(__name__)
app.config["SECRET_KEY"] = "securekey"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://labuser:123@localhost/torrenttracker"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Настройка Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["mail"]
        password = request.form["password"]
        user = User.query.filter_by(mail=email).first()
        if user and check_password_hash(user.user_password, password):
            login_user(user)
            log = Log(author_id=user.user_id, target_id=user.user_id, target_type="user", action_type="login")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for("index"))
        flash("Invalid email or password", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["mail"]
        password = generate_password_hash(request.form["password"], method="pbkdf2:sha256")
        role = request.form["role"]
        duplicate_user_by_name = User.query.filter_by(username=name).first()
        duplicate_user_by_mail = User.query.filter_by(mail=email).first()
        if not duplicate_user_by_name:
            flash("User with this name already exists", "danger")
            return redirect(url_for("register"))
        if not duplicate_user_by_mail:    
            flash("User with this mail already exists", "danger")
            return redirect(url_for("register"))
        user = User(username=name, mail=email, user_password=password, user_role=role)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        
        log = Log(author_id=user.user_id, target_id=user.user_id, target_type="user", action_type="registration")
        db.session.add(log)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    log = Log(author_id=current_user.user_id, target_id=current_user.user_id, target_type="user", action_type="logout")
    db.session.add(log)
    db.session.commit()
    logout_user()
    return redirect(url_for("index"))

@app.route("/users")
@login_required
def users():
    users = User.query.all()
    return render_template("users.html", users=users)

@app.route("/torrents")
@login_required
def torrents():
    torrents = Torrent.query.all()
    return render_template("torrents.html", torrents=torrents)

@app.route("/forum")
@login_required
def forum():
    posts = ForumPost.query.all()
    return render_template("forum.html", posts=posts)

@app.route("/my_activities")
@login_required
def activities():
    activities = Activity.query.filter_by(user_id=current_user.user_id).all
    return render_template("my_activities.html", activities=activities)

@app.route("/torrent/<int:torrent_id>")
@login_required
def torrent_info(torrent_id):
    torrent = Torrent.query.filter_by(torrent_id=torrent_id).first()
    comments = Comment.query.filter_by(torrent_id=torrent_id).all()
    if not torrent:
        flash("Torrent not found", "danger")
        return redirect(url_for("torrents"))
    return render_template("torrent_info.html", torrent=torrent, comments=comments)

@app.route("/logs")
@login_required
def logs():
    if current_user.user_role != "tmoderator" or current_user.user_role != "towner":
        flash("Access restricted", "danger")
        return redirect(url_for("index"))
    logs = Log.query.all()
    return render_template("logs.html", logs=logs)

@app.route("/torrent_upload", methods=["GET", "POST"])
@login_required
def upload_torrent():
    if request.method == "POST":
        title = request.form.get("title")
        hash_str = request.form.get("hash_string")
        description = request.form.get("description")
        author_id = current_user.user_id

        if not title or not hash_str or not description or not author_id:
            flash("Missing parameter", "danger")
            return redirect(url_for("torrent_upload"))
        
        duplicate_title = Torrent.query.filter_by(title=title).first()
        if duplicate_title:
            flash("Torrent with this title already exists", "danger")
            return redirect(url_for("torrent_upload"))
        duplicate_hash = Torrent.query.filter_by(hash_str=hash_str).first()
        if duplicate_hash:
            flash("Torrent hash string must be unique", "danger")
            return redirect(url_for("torrent_upload"))
        new_torrent = Torrent(hash_str=hash_str, title=title, description=description, author_id=author_id)
        highest_torrent_id = Torrent.query.order_by(Torrent.torrent_id.desc()).first()
        if highest_torrent_id.torrent_id:
            new_t_id = highest_torrent_id.torrent_id + 1
        else:
            new_t_id = 0
        db.session.add(new_torrent)
        flash("Torrent upload successfull", "success")
        
        log = Log(author_id=current_user.user_id, target_id=new_t_id, target_type="torrent", action_type="upload")
        db.session.add(log)
        db.session.commit()
        flash("Torrent uploaded", "success")
        return redirect(url_for("torrents"))
    render_template("torrent_upload.html")

@app.route("/comment_upload", methods=["GET", "POST"])
@login_required
def upload_comment():
    if request.method == "POST":
        get_t_title = request.form.get("title")
        user_id = current_user.user_id
        torrent_info = Torrent.query.filter_by(title=get_t_title).first()
        if not torrent_info:
            flash("Torrent not found", "danger")
            return redirect(url_for("comment_upload"))
        torrent_id = torrent_info.torrent_id
        comment_body = request.form.get("comment_body")
        if not torrent_id or not comment_body:
            flash("Missing parameter", "danger")
            return redirect(url_for("comment_upload"))
        new_comment = Comment(user_id=user_id, torrent_id=torrent_id, comment_body=comment_body)
        old_comment = Comment.query.order_by(comment_id=Comment.comment_id.desc()).first()
        if old_comment:
            new_comment_id = old_comment.comment_id + 1
        else:
            new_comment_id = 0
        log = Log(author_id=user_id, target_id=new_comment_id, target_type="comment", action_type="upload")
        db.sesion.add(new_comment)
        db.session.add(log)
        db.session.commit()
        flash("Comment uploaded", "success")
        return redirect(url_for("torrents"))
    render_template("comment_upload.html")
    
@app.route("/post_upload", methods=["GET", "POST"])
@login_required
def upload_post():
    if request.method == "POST":
        author_id=current_user.user_id
        post_title=request.form.get("ptitle")
        post_body=request.form.get("pbody")
        duplicate_title = Torrent.query.filter_by(post_title=post_title).first()
        if duplicate_title:
            flash("Post with this title already exist", "danger")
            return redirect(url_for("forum"))
        if not post_title or not post_body:
            flash("Missing parameter", "danger")
            return redirect(url_for("forum"))
        new_post = ForumPost(author_id=author_id, post_title=post_title, post_body=post_body)
        highest_post = ForumPost.query.order_by(ForumPost.post_id.desc()).first()
        if not highest_post:
            new_p_id = 1
        else:
            new_p_id = highest_post.post_id + 1 
        log = Log(author_id=author_id, target_id=new_p_id, target_type="forum_post", action_type="upload")
        db.session.add(new_post)
        db.session.add(log)
        db.session.commit()
        flash("Post uploaded", "success")
        return redirect(url_for("forum"))
    return render_template("post_upload.html")

@app.route("/add_user_rating", methods=["GET", "POST"])
@login_required
def add_user_rating():
    if request.method=="POST":
        targetusername=request.form.get("target_user_name")
        target_user = User.query.filter_by(username=targetusername).first()
        if target_user.user_id == current_user.user_id:
            flash("Cannot update own rating", "danger")
            return redirect(url_for("add_user_rating"))
        if not targetusername:
            flash("Missing parameter", "danger")
            return redirect(url_for("add_user_rating"))
        if not target_user:
            flash("User not found", "danger")
            return redirect(url_for("add_user_rating"))
        target_user.rating = target_user.rating + 1
        log = Log(author_id=current_user.user_id, target_id=target_user.user_id, target_type="user", action_type="add rating")
        db.session.add(log)
        db.session.commit()
        flash(f'Rating updated successfully. New rating: {target_user.rating}', "success")
        return redirect(url_for("users"))
    return render_template("add_user_rating.html")

@app.route("/delete_comment/<int:comment_id>", methods=["DELETE"])
@login_required
def delete_comment(comment_id, link_removal=False):
    comment_info = Comment.query.filter_by(comment_id=comment_id).first()
    if not comment_info:
        flash("Comment does not exist")
        return redirect(url_for("torrents"))
    if link_removal == False:
        if current_user.user_role != "tmoderator" or current_user.user_role != "towner" or current_user.user_id != torrent_info.author_id:
            flash("Action denied: don't have privilege")
            return redirect(url_for("torrents"))
    log = Log(author_id=current_user.user_id, target_id=comment_id, target_type="comment", action_type="delete")
    db.session.new(log)
    db.session.delete(comment_info)
    db.session.commit()
    if link_removal == False:
        flash("Removal successfull", "success")
        return redirect(url_for("torrents"))
    return

@app.route("/delete_torrent/<int:torrrent_id>", methods=["DELETE"])
@login_required
def delete_torrent(torrent_id):
    # make comments deletion first
    torrent_info = Torrent.query.filter_by(torrent_id=torrent_id).first()
    if not torrent_info:
        flash("Torrent does not exist")
        return redirect(url_for("torrents"))
    if current_user.user_role != "tmoderator" or current_user.user_role != "towner" or current_user.user_id != torrent_info.author_id:
        flash("Action denied: don't have privilege")
        return redirect(url_for("torrents"))
    comments_linked = Comment.query.filter_by(torrent_id=torrent_info.torrent_id).all()
    for i in comments_linked:
        delete_comment(i.comment_id, link_removal=True)
    log = Log(author_id=current_user.user_id, target_id=torrent_info.torrent_id, target_type="torrent", action_type="delete")
    db.session.add(log)
    db.session.delete(torrent_info)
    db.session.commit()
    flash("Removal successful", "success")
    return redirect(url_for("torrents"))

@app.route("/delete_post/<int:post_id>", methods=["DELETE"])
@login_required
def delete_post(post_id):
    post_info = ForumPost.query.filter_by(post_id=post_id).first()
    if not post_info:
        flash("Post does not exist")
        return redirect(url_for("forum"))
    if current_user.user_role != "tmoderator" or current_user.user_role != "towner" or current_user.user_id != post_info.author_id:
        flash("Action denied: don't have privilege")
        return redirect(url_for("forum"))
    log = Log(author_id=current_user.user_id, target_id=post_info.post_id, target_type="forum post", action_type="delete")
    db.session.add(log)
    db.session.delete(post_info)
    db.session.commit()
    flash("Removal successful", "success")
    return redirect(url_for("forum"))

@app.route("/change_user_role/<int:user_id>+<string:role>", methods=["POST"])
@login_required
def change_user_role(user_id, role):
    user_info = User.query.filter_by(user_id=user_id)
    if role != "guest" or role != "tuser" or role != "tmoderator" or role != "towner":
        flash("Role does not exist")
        return redirect(url_for("users"))
    if not user_info:
        flash("User does not exist")
        return redirect(url_for("users"))
    if current_user.user_role != "tmoderator" or current_user.user_role != "towner":
        flash("Action denied: don't have privilege")
        return redirect(url_for("users"))
    user_info.user_role = role
    log = Log(author_id=current_user.user_id, target_id=user_info.user_id, target_type="user", action_type="change role")
    db.session.add(log)
    db.session.commit()
    flash("Role changed", "success")
    return redirect(url_for("users"))

@app.route("/torrents/<int:torrent_id>/change_status", methods=["POST"])
@login_required
def change_torrent_status(torrent_id):
    torrent_info = Torrent.query.filter_by(torrent_id=torrent_id)
    if not torrent_info:
        flash("Torrent not found", "danger")
        return redirect(url_for("torrents"))
    # check activity
    activity_info = Activity.query.filter_by(torrent_id=torrent_id, user_id=current_user.user_id)
    last_activity = Activity.query.order_by(Activity.activity_id.desc()).first()
    if not activity_info:
        new_activity = Activity(user_id=current_user.user_id, torrent_id=torrent_id, action_type="peer")
        if not last_activity:
            log = Log(author_id=current_user.user_id, target_id=1, target_type="activity", action_type=f'new peer torrent id:{torrent_id}')
        else:
            log = Log(author_id=current_user.user_id, target_id=last_activity.activity_id+1, target_type="activity", action_type=f'new peer torrent id:{torrent_id}')
    elif activity_info.action_type == "peer":
        activity_info.action_type = "seed"
        log = Log(author_id=current_user.user_id, target_id=last_activity.activity_id+1, target_type="activity", action_type=f'change to seed torrent id:{torrent_id}')
    elif activity_info.action_type == "seed":
        activity_info.action_type = "peer"
        log = Log(author_id=current_user.user_id, target_id=last_activity.activity_id+1, target_type="activity", action_type=f'change to peer torrent id:{torrent_id}')
    db.session.add(log)
    db.session.commit()
    flash("Activity created", "success")
    return redirect(url_for("my_activities"))

@app.route("/my_activities/<int:torrent_id>", methods=["DELETE"])
@login_required
def remove_activity(torrent_id):
    activity_info = Activity.query.filter_by(torrent_id=torrent_id, user_id=current_user.user_id)
    if not activity_info:
        flash("Activity does not exist", "danger")
        return redirect(url_for("my_activities"))
    log = Log(author_id=current_user.user_id, target_id=activity_info.activity_id, target_type="activity", action_type=f'removed seed/peer torrent id:{torrent_id}')
    db.session.delete(activity_info)
    db.session.add(log)
    flash("Activity removed", "success")
    return redirect(url_for("my_activities"))

    

# Запуск приложения
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
