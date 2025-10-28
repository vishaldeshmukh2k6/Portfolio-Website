from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
from flask import session
from functools import wraps
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

#  Models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    github_link = db.Column(db.String(250))
    live_link = db.Column(db.String(250))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VisitorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(250))
    path = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ProductMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    issuer = db.Column(db.String(150), nullable=False)
    issued_date = db.Column(db.String(50), nullable=False)
    link = db.Column(db.String(250))

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer, nullable=False, default=18)

# --- Visitor Logger ---
@app.before_request
def log_visitor():
    if request.endpoint not in ["static"]:
        new_log = VisitorLog(ip=request.remote_addr,user_agent=request.headers.get("User-Agent"),path=request.path)
        db.session.add(new_log)
        db.session.commit()

# --- Routes ---
@app.route("/")
def home():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    certificates = Certificate.query.order_by(Certificate.id.desc()).all()
    return render_template("index.html", projects=projects, certificates=certificates)

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message_text = request.form.get("message")
    if not name or not email or not message_text:
        flash("Please fill all fields!", "danger")
        return redirect(url_for("home"))
    try:
        msg = Message(subject=f"Portfolio Contact from {name}",sender=email,recipients=[app.config['MAIL_USERNAME']],body=f"From: {name}\nEmail: {email}\n\nMessage:\n{message_text}")
        mail.send(msg)
        flash("Message sent successfully!", "success")
    except Exception as e:
        flash(f"Error sending message: {e}", "danger")

    return redirect(url_for("home"))

@app.route("/resume")
def resume():
    return send_file("static/resume.pdf", as_attachment=True)

# --- API Endpoints ---
@app.route("/api/projects")
def api_projects():
    projects = Project.query.all()
    return jsonify([{"title": p.title,"description": p.description,"github": p.github_link,"live": p.live_link} for p in projects])


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# --- Admin Dashboard ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    logs = VisitorLog.query.order_by(VisitorLog.timestamp.desc()).limit(20).all()
    projects = Project.query.all()
    messages = ProductMessage.query.order_by(ProductMessage.created_at.desc()).all()
    certificates = Certificate.query.all()
    profile = Profile.query.first()
    current_year = datetime.now().year
    age = profile.age if profile else ""
    return render_template("admin.html", logs=logs, projects=projects, messages=messages, certificates=certificates, age=age, year=current_year)
# Authentication Decorator

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == os.getenv("ADMIN_USER") and password == os.getenv("ADMIN_PASS"):
            session["admin_logged_in"] = True
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


# --- Project Management ---
@app.route("/admin/project/add", methods=["POST"])
def add_project():
    title = request.form.get("title")
    description = request.form.get("description")
    github_link = request.form.get("github")
    live_link = request.form.get("live")
    new_project = Project(title=title,description=description,github_link=github_link,live_link=live_link)
    db.session.add(new_project)
    db.session.commit()
    flash("Project added successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/project/delete/<int:id>", methods=["POST"])
def delete_project(id):
    p = Project.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash("Project deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Product Messages Admin ---
@app.route("/admin/messages/delete/<int:id>", methods=["POST"])
def delete_message(id):
    msg = ProductMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Certificates Admin ---
@app.route("/admin/certificate/add", methods=["POST"])
def add_certificate():
    title = request.form.get("title")
    issuer = request.form.get("issuer")
    issued_date = request.form.get("issued_date")
    link = request.form.get("link")

    new_c = Certificate(title=title, issuer=issuer,issued_date=issued_date, link=link)
    db.session.add(new_c)
    db.session.commit()
    flash("Certificate added successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/certificate/delete/<int:id>", methods=["POST"])
def delete_certificate(id):
    c = Certificate.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash("Certificate deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Profile Age ---
@app.route("/admin/update_age", methods=["POST"])
def update_age():
    age = request.form.get("age")
    profile = Profile.query.first()
    if profile:
        profile.age = age
    else:
        profile = Profile(age=age)
        db.session.add(profile)
    db.session.commit()
    flash("Age updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500


# --- Main ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
