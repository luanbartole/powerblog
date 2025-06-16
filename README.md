# PowerBlog

A simple blog app built with Flask. It supports user registration, login, blog post creation, and commenting. Only the admin can create and manage posts.

🟢 Live site: [https://powerblog-lj3k.onrender.com](https://powerblog-lj3k.onrender.com)

---

## Features

* Admin-only post creation/editing
* User registration & login
* Comment system
* Rich text editor (CKEditor)
* Gravatar support for avatars
* Bootstrap layout

---

## Tech Stack

* Flask + Jinja
* SQLAlchemy
* Flask-Login
* Flask-WTF
* CKEditor
* SQLite (dev)
* Bootstrap 5

---

## Setup

1. **Clone the repo**
   `git clone https://github.com/your-username/powerblog.git`

2. **Create a virtual environment**
   `python -m venv venv && source venv/bin/activate`
   (Windows: `venv\Scripts\activate`)

3. **Install dependencies**
   `pip install -r requirements.txt`

4. **Set up environment variables**
   Create a `.env` file and add:

   ```
   FLASK_KEY=your-secret-key # Secret key for Flask session & CSRF protection
   PYTHON_EMAIL=yourbot@example.com # Email address used by the app to send notifications
   PYTHON_EMAIL_PASSWORD=yourbotpassword # Password for the above email account
   USER_EMAIL=youruser@example.com # Recipient email for notifications or contact

   ```

5. **Run the app**
   `flask run`

---

## Notes

* Admin is the first user to register.
* Comments are only allowed if you're logged in.
* No external DB needed — uses SQLite by default.

---

## License

MIT
