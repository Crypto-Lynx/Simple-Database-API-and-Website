from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash


# Модели
from models import db, User, Torrent, Activity, Comment, ForumPost, ModerationLog, UserRole, UserRoleAssignment

# Нсатройки приложения
app = Flask(__name__)
app.config["SECRET_KEY"] = "securekey"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://labuser:123@localhost/torrent_tracker"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Настройка Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Роуты

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/torrents")
def torrents():
    torrents = Torrent.query.all()
    return render_template("torrents.html", torrents=torrents)

@app.route("/users")
def users():
    users = User.query.all()
    return render_template("users.html", users=users)

@app.route("/forumposts")
def forumposts():
    forumposts = ForumPost.query.all()
    return render_template("forumposts.html", forumposts=forumposts)

@app.route("/download_torrent/<int:torrent_id>", methods=["POST"])
@login_required
def download_torrent(torrent_id):
    # Получаем объект торрента по torrent_id
    torrent = Torrent.query.get(torrent_id)
    if not torrent:
        flash("Torrent not found", "danger")
        return redirect(url_for("torrents"))
    
    # Проверяем наличие активности "seed" для текущего пользователя и данного торрента
    seed_status = Activity.query.filter_by(
        user_id=current_user.user_id,
        torrent_id=torrent_id,
        action_type='seed'
    ).first()

    if seed_status:
        flash("torrent already seeding", "danger")
        return redirect(url_for("torrents"))

    # Проверяем наличие активности "download" для текущего пользователя и данного торрента
    download_status = Activity.query.filter_by(
        user_id=current_user.user_id,
        torrent_id=torrent_id,
        action_type='download'
    ).first()

    if download_status:
        flash("torrent already downloading", "danger")
        return redirect(url_for("torrents"))

    # Если активности нет, добавляем новую запись "download"
    new_activity = Activity(
        user_id=current_user.user_id,
        torrent_id=torrent_id,
        action_type='download'
    )
    db.session.add(new_activity)
    db.session.commit()
    flash("download started", "success")
    return redirect(url_for("torrents"))

@app.route("/change_torrent_status/<int:torrent_id>", methods=["POST"])
@login_required
def change_torrent_status(torrent_id):
    # Получаем тип действия от пользователя ('seed' или 'delete')
    action_type = request.form.get("action_type")
    
    # Проверяем существование торрента
    torrent = Torrent.query.filter_by(torrent_id=torrent_id).first()
    if not torrent:
        flash("Torrent not found", "danger")
        return redirect(url_for("torrents"))

    # Проверяем, есть ли запись в Activity для текущего пользователя и торрента
    activity = Activity.query.filter_by(user_id=current_user.user_id, torrent_id=torrent_id).first()

    if action_type == "seed":
        # Пользователь может раздавать только те торренты, которые он скачал
        if activity and activity.action_type == "download":
            # Обновляем статус на 'seed'
            activity.action_type = "seed"
            db.session.commit()
            flash("Torrent status updated to 'seed'", "success")
            return redirect(url_for("torrents"))
        elif activity and activity.action_type == "seed":
            flash("Torrent is already being seeded", "danger")
            return redirect(url_for("torrents"))
        else:
            flash("User must download the torrent before seeding", "danger")
            return redirect(url_for("torrents"))

    elif action_type == "delete":
        # Удаление записи, если пользователь ничего больше не делает с торрентом
        if activity:
            db.session.delete(activity)
            db.session.commit()
            flash("Activity deleted successfully", "success")
            return redirect(url_for("torrents"))
        else:
            flash("No activity found for the given torrent", "danger")
            return redirect(url_for("torrents"))
    else:
        flash("Invalid action type", "danger")
        return redirect(url_for("torrents"))

@app.route("/download_torrent/<int:torrent_id>", methods=["GET"])
@login_required
def view_torrent(torrent_id):
    torrent_info = Torrent.query.filter_by(torrent_id=torrent_id).first()
    comments = Comment.query.filter_by(torrent_id=torrent_id).all()
    return render_template("torrent.html", torrent_info=torrent_info, comments=comments)

@app.route("/my_actions")
@login_required
def view_actions():
    actions = Activity.query.filter_by(user_id=current_user.user_id).all()
    return render_template("my_actions.html", actions=actions)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            log = ModerationLog(user_id=user.user_id, action="Login")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"], method="pbkdf2:sha256")
        role = request.form["role"]
        user = User(name=name, email=email, password=password, role=role, registration_date=db.func.current_date())
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        
        log = ModerationLog(user_id=user.user_id, action="Registration")
        db.session.add(log)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/moderation_log")
@login_required
def moderation_log():
    user_role_assignment = (
    UserRoleAssignment.query
    .filter_by(user_id=current_user.user_id)
    .join(UserRole, UserRole.role_id == UserRoleAssignment.role_id)
    .filter(UserRole.role_name == "moderator")
    .first()
    )
    if user_role_assignment is not None:
        users = User.query.all()
        mod_logs = ModerationLog.query.order_by(ModerationLog.time.desc()).all()
        return render_template("moderation_log.html", users=users, mod_logs=mod_logs)
    else:
        flash("Unauthorized access", "danger")
        return redirect(url_for("logout"))
    

@app.route('/change_role/<int:user_id>', methods=['POST'])
@login_required
def change_role(user_id):
    new_role = request.form.get('role_name')  # Новая роль, которую нужно назначить

    # Проверка: текущий пользователь не может менять свою роль
    if current_user.user_id == user_id:
        flash("You cannot change your own role.", "danger")
        return redirect(url_for("users"))

    # Получение пользователя, чья роль должна быть изменена
    user_to_change = User.query.get(user_id)
    if not user_to_change:
        flash("User not found.", "danger")
        return redirect(url_for("users"))

    # Получение текущих ролей пользователей
    current_user_roles = db.session.query(UserRole).join(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == current_user.user_id
    ).all()

    user_to_change_roles = db.session.query(UserRole).join(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == user_id
    ).all()

    # Проверка: текущий пользователь должен быть модератором или владельцем
    allowed_roles = {"moderator", "owner"}
    current_user_role_names = {role.role_name for role in current_user_roles}
    if not current_user_role_names & allowed_roles:
        flash("You do not have permission to change roles.", "danger")
        return redirect(url_for("users"))

    # Проверка: новая роль должна существовать
    role_to_assign = UserRole.query.filter_by(role_name=new_role).first()
    if not role_to_assign:
        flash("The specified role does not exist.", "danger")
        return redirect(url_for("users"))

    # Проверка: модератор не может менять роль владельцу
    if "moderator" in current_user_role_names and "owner" in {role.role_name for role in user_to_change_roles}:
        flash("Moderators cannot change the role of an owner.", "danger")
        return redirect(url_for("users"))

    # Проверка: владелец может менять роль модератора
    if "owner" in current_user_role_names or "moderator" in current_user_role_names:
        # Удаляем текущие роли пользователя
        UserRoleAssignment.query.filter_by(user_id=user_id).delete()

        # Добавляем новую роль
        new_assignment = UserRoleAssignment(user_id=user_id, role_id=role_to_assign.role_id)
        db.session.add(new_assignment)
        db.session.commit()
        flash(f"Role updated to {new_role}.", "success")
        return redirect(url_for("users"))

    flash("You cannot perform this action.", "danger")
    return redirect(url_for("users"))

@app.route("/create_post", methods=["POST"])
@login_required
def create_post():
    title = request.form.get("title")
    content = request.form.get("content")

    if not title or not content:
        flash("Title and content are required", "danger")
        return redirect(url_for("forum_posts"))

    # Check if the user already has a post with the same title
    existing_post = ForumPost.query.filter_by(user_id=current_user.user_id, title=title).first()
    if existing_post:
        flash("You already have a post with this title","danger")
        return redirect(url_for("forum_posts"))

    # Create a new post
    new_post = ForumPost(user_id=current_user.user_id, title=title, content=content)

    try:
        db.session.add(new_post)
        db.session.commit()
        flash("Post created successfully","success")
        return redirect(url_for("forum_posts"))
    except IntegrityError:
        db.session.rollback()
        flash("A post with this title already exists","danger")
        return redirect(url_for("forum_posts"))

@app.route("/delete_post/<int:post_id>", methods=["DELETE"])
@login_required
def delete_post(post_id):
    post = ForumPost.query.get(post_id)

    if not post:
        flash("Post not found","danger")
        return redirect(url_for("forum_posts"))

    # Check if the current user is allowed to delete the post
    user_roles = (
        db.session.query(UserRole.role_name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == UserRole.role_id)
        .filter(UserRoleAssignment.user_id == current_user.user_id)
        .all()
    )
    user_roles = {role[0] for role in user_roles}

    if current_user.user_id != post.user_id and not ("moderator" in user_roles or "owner" in user_roles):
        flash("You do not have permission to delete this post","danger")
        return redirect(url_for("forum_posts"))

    # Moderators cannot delete posts created by the owner
    post_owner_roles = (
        db.session.query(UserRole.role_name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == UserRole.role_id)
        .filter(UserRoleAssignment.user_id == post.user_id)
        .all()
    )
    post_owner_roles = {role[0] for role in post_owner_roles}

    if "owner" in post_owner_roles and "moderator" in user_roles:
        flash("Moderators cannot delete posts created by the owner","danger")
        return redirect(url_for("forum_posts"))

    # Delete the post
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully","success")
    return redirect(url_for("forum_posts"))

@app.route('/add_rating/<int:user_id>', methods=['POST'])
@login_required
def add_rating(user_id):
    # Получение значения рейтинга из запроса
    try:
        rating_to_add = int(request.form.get('rating', 0))
    except ValueError:
        flash('Invalid rating value. It must be an integer.', "danger")
        return redirect(url_for("users"))

    # Проверка диапазона значения рейтинга
    if not (1 <= rating_to_add <= 10):
        flash('Rating must be between 1 and 10.', "danger")
        return redirect(url_for("users"))

    # Поиск пользователя
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        flash('User not found.', "danger")
        return redirect(url_for("users"))

    # Обновление рейтинга
    user.rating += rating_to_add
    db.session.commit()
    flash(f'Rating updated successfully. New rating: {user.rating}', "success")
    return redirect(url_for("users"))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    # Проверяем, что пользователь, которого нужно удалить, существует
    user_to_delete = User.query.get(user_id)
    if not user_to_delete:
        flash('User not found.', "danger")
        return redirect(url_for("users"))

    # Проверяем роли текущего пользователя
    current_user_roles = db.session.query(UserRole.role_name).join(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == current_user.user_id
    ).all()
    current_user_roles = [role[0] for role in current_user_roles]

    if "owner" not in current_user_roles and "moderator" not in current_user_roles:
        flash("You do not have permission to delete users", "danger")
        return redirect(url_for("users"))

    # Ограничение для модератора
    if "moderator" in current_user_roles and "owner" in db.session.query(UserRole.role_name).join(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == user_id
    ).first():
        flash("Moderators cannot delete owners", "danger")
        return redirect(url_for("users"))

    # Удаляем связанные данные из таблиц (каскадное удаление)
    Activity.query.filter_by(user_id=user_id).delete()
    UserRoleAssignment.query.filter_by(user_id=user_id).delete()
    ForumPost.query.filter_by(user_id=user_id).delete()

    # Удаляем пользователя
    db.session.delete(user_to_delete)
    db.session.commit()

    flash("User deleted successfully", "success")
    return redirect(url_for("users"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Запуск приложения
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
