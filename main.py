from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from typing import List
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import os
import smtplib

# -----------------------------
# App & Extension Initialization
# -----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
BOT_EMAIL = os.environ.get("PYTHON_EMAIL")
BOT_EMAIL_PASSWORD = os.environ.get("PYTHON_EMAIL_PASSWORD")
user_email = os.environ.get("USER_EMAIL")


# Initialize CKEditor for rich text editing in posts
ckeditor = CKEditor(app)

# Apply Bootstrap styles
Bootstrap5(app)

# Set up Gravatar for user profile images based on email
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro')

# Initialize Flask-Login for user authentication management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# -----------------------------
# Database Setup
# -----------------------------
class Base(DeclarativeBase):
    pass


# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# -----------------------------
# Models
# -----------------------------
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    email: Mapped[str] = mapped_column(String(250), unique=True)
    password: Mapped[str] = mapped_column(String(250))

    # Relationships
    posts: Mapped[List["BlogPost"]] = relationship(back_populates="author")
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    # Foreign key linking to User (author)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    author: Mapped["User"] = relationship(back_populates="posts")

    # One post can have many comments
    comments: Mapped[List["Comment"]] = relationship(back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Foreign keys linking to User and BlogPost
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    author: Mapped["User"] = relationship(back_populates="comments")

    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    parent_post: Mapped["BlogPost"] = relationship(back_populates="comments")


# Create all tables
with app.app_context():
    db.create_all()


# -----------------------------
# Flask-Login User Loader
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -----------------------------
# Access Control Decorators
# -----------------------------

def admin_only(f):
    """Allow only admin user (user with ID = 1)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


def only_commenter(function):
    """Allow only the author of a comment to delete it"""

    @wraps(function)
    def decorated_function(comment_id, *args, **kwargs):
        comment = db.get_or_404(Comment, comment_id)
        if not current_user.is_authenticated or current_user.id != comment.author_id:
            return abort(403)
        return function(comment_id=comment_id, *args, **kwargs)

    return decorated_function


# -----------------------------
# Routes
# -----------------------------

@app.route('/')
def get_all_posts():
    """Homepage: Show all blog posts"""
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    """Single blog post page with comment form"""
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comment(
            text=comment_form.comment.data,
            author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)


@app.route('/register', methods=["GET", "POST"])
def register():
    """User registration"""
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.execute(db.select(User).filter_by(email=request.form.get('email'))).scalar():
            flash("User already exists, please log in.")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            password=request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            name=request.form.get('name'),
            email=request.form.get('email'),
            password=hash_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """User login"""
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if not user:
            flash("That email does not exist. Please try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(user.password, password):
            flash("Invalid password. Please try again.")
            return redirect(url_for("login"))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    """Create new blog post (admin only)"""
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    """Edit existing blog post (admin only)"""
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    """Delete a blog post (admin only)"""
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete/comment/<int:comment_id>/<int:post_id>")
@only_commenter
def delete_comment(comment_id, post_id):
    """Delete a comment (only by the author)"""
    comment_to_delete = db.get_or_404(Comment, comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for("show_post", post_id=post_id))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact.html", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form  # Collect data submitted in the form

        # Send the form data via email using SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()  # Secure the connection
            connection.login(BOT_EMAIL, BOT_EMAIL_PASSWORD)
            connection.sendmail(
                from_addr=BOT_EMAIL,
                to_addrs=user_email,
                msg=f"Subject: Blog Contact Form - {data['username']} \n\n"
                    f"Message: {data['message']} \n\n"
                    f"Email: {data['email']} Phone Number: {data['phone']}"
            )

        # Show a success message to the user
        return "<h1>Successfully sent your message</h1>"

    # Render the contact form template if it's a GET request
    return render_template("contact.html")


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=False, port=5000, host="localhost")