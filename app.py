from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
import os
import requests
import json
from collections import defaultdict
import secrets
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx'}

# Security configurations
app.config['WTF_CSRF_TIME_LIMIT'] = 3600
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True only with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Initialize security extensions
csrf = CSRFProtect(app)
talisman = Talisman(
    app,
    force_https=False,  # Set to True in production
    strict_transport_security=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com",
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        'img-src': "'self' data: https:",
        'connect-src': "'self'"
    }
)

# Rate limiting with proper storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
limiter.init_app(app)

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

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Frontend, Backend, Database, etc.
    proficiency = db.Column(db.Integer, nullable=False)  # 1-100
    years_experience = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    tags = db.Column(db.String(500))  # Comma-separated
    published = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    read_time = db.Column(db.Integer, default=5)  # minutes
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CodeSnippet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    language = db.Column(db.String(50), nullable=False)
    code = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(500))
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')  # general, project, job, collaboration
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    status = db.Column(db.String(20), default='new')  # new, read, replied, closed
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GitHubStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    public_repos = db.Column(db.Integer, default=0)
    followers = db.Column(db.Integer, default=0)
    following = db.Column(db.Integer, default=0)
    total_stars = db.Column(db.Integer, default=0)
    total_forks = db.Column(db.Integer, default=0)
    most_used_language = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

@app.before_request
def before_request():
    # Visitor logging
    if request.endpoint not in ["static"]:
        new_log = VisitorLog(
            ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            path=request.path
        )
        db.session.add(new_log)
        try:
            db.session.commit()
        except:
            db.session.rollback()

@app.after_request
def after_request(response):
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# --- Routes ---
@app.route("/")
def home():
    projects = Project.query.order_by(Project.created_at.desc()).limit(6).all()
    certificates = Certificate.query.order_by(Certificate.id.desc()).limit(6).all()
    skills = Skill.query.order_by(Skill.proficiency.desc()).all()
    featured_posts = BlogPost.query.filter_by(published=True, featured=True).limit(3).all()
    code_snippets = CodeSnippet.query.filter_by(featured=True).limit(4).all()
    github_stats = GitHubStats.query.first()
    
    # Update GitHub stats if older than 1 hour
    if not github_stats or github_stats.last_updated < datetime.utcnow() - timedelta(hours=1):
        update_github_stats()
        github_stats = GitHubStats.query.first()
    
    return render_template("index.html", 
                         projects=projects, 
                         certificates=certificates,
                         skills=skills,
                         featured_posts=featured_posts,
                         code_snippets=code_snippets,
                         github_stats=github_stats)

@app.route("/contact", methods=["POST"])
@limiter.limit("5 per minute")
def contact():
    # Sanitize inputs
    name = sanitize_input(request.form.get("name"))
    email = sanitize_input(request.form.get("email"))
    subject = sanitize_input(request.form.get("subject", "General Inquiry"))
    message_text = sanitize_input(request.form.get("message"))
    category = sanitize_input(request.form.get("category", "general"))
    
    # Validate inputs
    if not name or not email or not message_text:
        flash("Please fill all required fields!", "danger")
        return redirect(url_for("home"))
    
    if not validate_email(email):
        flash("Please enter a valid email address!", "danger")
        return redirect(url_for("home"))
    
    if len(name) < 2 or len(message_text) < 10:
        flash("Name must be at least 2 characters and message at least 10 characters!", "danger")
        return redirect(url_for("home"))
    
    # Check for spam patterns
    spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'congratulations', 'click here']
    if any(keyword in message_text.lower() for keyword in spam_keywords):
        flash("Message appears to be spam and was not sent.", "danger")
        return redirect(url_for("home"))
    
    # Determine priority based on keywords
    priority = "normal"
    urgent_keywords = ["urgent", "asap", "emergency", "critical", "job", "opportunity"]
    if any(keyword in message_text.lower() or keyword in subject.lower() for keyword in urgent_keywords):
        priority = "high"
    
    try:
        # Save to database
        inquiry = ContactInquiry(
            name=name,
            email=email,
            subject=subject,
            message=message_text,
            category=category,
            priority=priority,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500]
        )
        db.session.add(inquiry)
        
        msg = Message(
            subject=f"[{priority.upper()}] Portfolio Contact: {subject}",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']],
            body=f"From: {name}\nEmail: {email}\nCategory: {category}\nPriority: {priority}\n\nMessage:\n{message_text}"
        )
        mail.send(msg)
        db.session.commit()
        flash("Message sent successfully! I'll get back to you soon.", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Contact form error: {e}")
        flash("Error sending message. Please try again later.", "danger")

    return redirect(url_for("home"))

@app.route("/resume")
def resume():
    return send_file("static/resume.pdf", as_attachment=True)

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "Portfolio app is running"}), 200



# --- API Endpoints ---
@app.route("/api/projects")
@limiter.limit("100 per hour")
def api_projects():
    projects = Project.query.all()
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "github": p.github_link,
        "live": p.live_link,
        "created_at": p.created_at.isoformat()
    } for p in projects])

@app.route("/api/skills")
@limiter.limit("100 per hour")
def api_skills():
    skills = Skill.query.all()
    skills_by_category = defaultdict(list)
    for skill in skills:
        skills_by_category[skill.category].append({
            "name": skill.name,
            "proficiency": skill.proficiency,
            "years_experience": skill.years_experience
        })
    return jsonify(dict(skills_by_category))

@app.route("/api/github-stats")
@limiter.limit("50 per hour")
def api_github_stats():
    stats = GitHubStats.query.first()
    if not stats:
        return jsonify({"error": "No GitHub stats available"}), 404
    
    return jsonify({
        "public_repos": stats.public_repos,
        "followers": stats.followers,
        "following": stats.following,
        "total_stars": stats.total_stars,
        "total_forks": stats.total_forks,
        "most_used_language": stats.most_used_language,
        "last_updated": stats.last_updated.isoformat()
    })

@app.route("/blog")
def blog():
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    
    search = sanitize_input(request.args.get('search', ''))[:100]
    tag = sanitize_input(request.args.get('tag', ''))[:50]
    
    query = BlogPost.query.filter_by(published=True)
    
    if search and len(search) >= 2:
        query = query.filter(BlogPost.title.contains(search) | BlogPost.content.contains(search))
    
    if tag:
        query = query.filter(BlogPost.tags.contains(tag))
    
    try:
        posts = query.order_by(BlogPost.created_at.desc()).paginate(
            page=page, per_page=6, error_out=False, max_per_page=20
        )
    except Exception as e:
        app.logger.error(f"Blog pagination error: {e}")
        posts = query.order_by(BlogPost.created_at.desc()).paginate(
            page=1, per_page=6, error_out=False
        )
    
    # Get all tags for filter
    all_tags = set()
    try:
        all_posts = BlogPost.query.filter_by(published=True).all()
        for post in all_posts:
            if post.tags:
                tags = [sanitize_input(tag.strip()) for tag in post.tags.split(',')]
                all_tags.update([tag for tag in tags if tag])
    except Exception as e:
        app.logger.error(f"Error getting tags: {e}")
    
    return render_template('blog.html', posts=posts, all_tags=sorted(all_tags), current_search=search, current_tag=tag)

@app.route("/blog/<slug>")
def blog_post(slug):
    # Sanitize slug to prevent path traversal
    slug = re.sub(r'[^a-zA-Z0-9-]', '', slug)
    if not slug:
        abort(404)
    
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    
    try:
        # Increment view count
        post.views += 1
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error updating view count: {e}")
        db.session.rollback()
    
    # Get related posts
    related_posts = []
    if post.tags:
        tags = [sanitize_input(tag.strip()) for tag in post.tags.split(',')]
        for tag in tags[:2]:  # Use first 2 tags
            if tag:  # Only process non-empty tags
                related = BlogPost.query.filter(
                    BlogPost.tags.contains(tag),
                    BlogPost.id != post.id,
                    BlogPost.published == True
                ).limit(3).all()
                related_posts.extend(related)
    
    # Remove duplicates and limit
    related_posts = list({p.id: p for p in related_posts}.values())[:3]
    
    return render_template('blog_post.html', post=post, related_posts=related_posts)

@app.route("/code-snippets")
def code_snippets():
    language = sanitize_input(request.args.get('language', ''))[:50]
    search = sanitize_input(request.args.get('search', ''))[:100]
    
    query = CodeSnippet.query
    
    if language:
        query = query.filter_by(language=language)
    
    if search and len(search) >= 2:
        query = query.filter(CodeSnippet.title.contains(search) | CodeSnippet.description.contains(search))
    
    try:
        snippets = query.order_by(CodeSnippet.created_at.desc()).all()
        
        # Get all languages for filter
        languages = db.session.query(CodeSnippet.language).distinct().all()
        languages = [sanitize_input(lang[0]) for lang in languages if lang[0]]
        
    except Exception as e:
        app.logger.error(f"Code snippets error: {e}")
        snippets = []
        languages = []
    
    return render_template('code_snippets.html', snippets=snippets, languages=languages, current_language=language, current_search=search)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login first!", "warning")
            return redirect(url_for("login"))
        # Check session timeout
        if session.get('last_activity'):
            if datetime.utcnow() - session['last_activity'] > timedelta(hours=1):
                session.clear()
                flash("Session expired. Please login again.", "warning")
                return redirect(url_for("login"))
        session['last_activity'] = datetime.utcnow()
        return f(*args, **kwargs)
    return decorated_function

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', str(text))
    return text.strip()[:1000]  # Limit length

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Admin Dashboard ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    logs = VisitorLog.query.order_by(VisitorLog.timestamp.desc()).limit(20).all()
    projects = Project.query.all()
    messages = ProductMessage.query.order_by(ProductMessage.created_at.desc()).all()
    certificates = Certificate.query.all()
    profile = Profile.query.first()
    skills = Skill.query.all()
    blog_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(10).all()
    code_snippets = CodeSnippet.query.order_by(CodeSnippet.created_at.desc()).limit(10).all()
    inquiries = ContactInquiry.query.order_by(ContactInquiry.created_at.desc()).limit(20).all()
    github_stats = GitHubStats.query.first()
    
    # Recent activity stats
    stats = {
        'total_projects': len(projects),
        'total_blog_posts': BlogPost.query.filter_by(published=True).count(),
        'total_skills': len(skills),
        'total_inquiries': ContactInquiry.query.count(),
        'unread_inquiries': ContactInquiry.query.filter_by(status='new').count(),
        'high_priority_inquiries': ContactInquiry.query.filter_by(priority='high', status='new').count()
    }
    
    current_year = datetime.now().year
    age = profile.age if profile else ""
    
    return render_template("admin.html", 
                         logs=logs, 
                         projects=projects, 
                         messages=messages, 
                         certificates=certificates, 
                         skills=skills,
                         blog_posts=blog_posts,
                         code_snippets=code_snippets,
                         inquiries=inquiries,
                         github_stats=github_stats,

                         stats=stats,
                         age=age, 
                         year=current_year)
# Authentication Decorator

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = sanitize_input(request.form.get("username"))
        password = request.form.get("password", "")
        
        # Rate limiting for failed attempts
        failed_attempts_key = f"failed_login:{request.remote_addr}"
        
        if not username or not password:
            flash("Please enter both username and password", "danger")
            return render_template("login.html")
        
        # Check credentials
        if username == os.getenv("ADMIN_USER") and password == os.getenv("ADMIN_PASS"):
            session["admin_logged_in"] = True
            session["last_activity"] = datetime.utcnow()
            session.permanent = True
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            # Log failed attempt
            app.logger.warning(f"Failed login attempt from {request.remote_addr} for user {username}")
            flash("Invalid username or password", "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


# --- Project Management ---
@app.route("/admin/project/add", methods=["POST"])
@admin_required
def add_project():
    title = sanitize_input(request.form.get("title"))
    description = sanitize_input(request.form.get("description"))
    github_link = sanitize_input(request.form.get("github"))
    live_link = sanitize_input(request.form.get("live"))
    
    if not title or not description:
        flash("Title and description are required!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    # Validate URLs if provided
    url_pattern = r'^https?://[\w\.-]+\.[a-zA-Z]{2,}'
    if github_link and not re.match(url_pattern, github_link):
        flash("Invalid GitHub URL format!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if live_link and not re.match(url_pattern, live_link):
        flash("Invalid live URL format!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    try:
        new_project = Project(title=title, description=description, github_link=github_link, live_link=live_link)
        db.session.add(new_project)
        db.session.commit()
        flash("Project added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding project: {e}")
        flash("Error adding project!", "danger")
    
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

# --- Skills Management ---
@app.route("/admin/skill/add", methods=["POST"])
@admin_required
def add_skill():
    name = sanitize_input(request.form.get("name"))
    category = sanitize_input(request.form.get("category"))
    
    try:
        proficiency = int(request.form.get("proficiency", 50))
        years_experience = float(request.form.get("years_experience", 0))
    except (ValueError, TypeError):
        flash("Invalid proficiency or experience values!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if not name or not category:
        flash("Name and category are required!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if proficiency < 1 or proficiency > 100:
        flash("Proficiency must be between 1 and 100!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if years_experience < 0 or years_experience > 50:
        flash("Years of experience must be between 0 and 50!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    try:
        skill = Skill(name=name, category=category, proficiency=proficiency, years_experience=years_experience)
        db.session.add(skill)
        db.session.commit()
        flash("Skill added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding skill: {e}")
        flash("Error adding skill!", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/skill/delete/<int:id>", methods=["POST"])
@admin_required
def delete_skill(id):
    skill = Skill.query.get_or_404(id)
    db.session.delete(skill)
    db.session.commit()
    flash("Skill deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Blog Management ---
@app.route("/admin/blog/add", methods=["POST"])
@admin_required
def add_blog_post():
    title = sanitize_input(request.form.get("title"))
    content = request.form.get("content", "")  # Don't sanitize content as it may contain HTML
    excerpt = sanitize_input(request.form.get("excerpt"))
    tags = sanitize_input(request.form.get("tags"))
    published = bool(request.form.get("published"))
    featured = bool(request.form.get("featured"))
    
    try:
        read_time = int(request.form.get("read_time", 5))
    except (ValueError, TypeError):
        read_time = 5
    
    if not title or not content:
        flash("Title and content are required!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if read_time < 1 or read_time > 120:
        flash("Read time must be between 1 and 120 minutes!", "danger")
        return redirect(url_for("admin_dashboard"))
    
    # Generate slug from title
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
    slug = re.sub(r'\s+', '-', slug).strip('-')
    
    # Ensure unique slug
    original_slug = slug
    counter = 1
    while BlogPost.query.filter_by(slug=slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    try:
        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            tags=tags,
            published=published,
            featured=featured,
            read_time=read_time
        )
        db.session.add(post)
        db.session.commit()
        flash("Blog post added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding blog post: {e}")
        flash("Error adding blog post!", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/blog/delete/<int:id>", methods=["POST"])
@admin_required
def delete_blog_post(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash("Blog post deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Code Snippets Management ---
@app.route("/admin/snippet/add", methods=["POST"])
@admin_required
def add_code_snippet():
    title = request.form.get("title")
    description = request.form.get("description")
    language = request.form.get("language")
    code = request.form.get("code")
    tags = request.form.get("tags")
    featured = bool(request.form.get("featured"))
    
    snippet = CodeSnippet(
        title=title,
        description=description,
        language=language,
        code=code,
        tags=tags,
        featured=featured
    )
    db.session.add(snippet)
    db.session.commit()
    flash("Code snippet added successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/snippet/delete/<int:id>", methods=["POST"])
@admin_required
def delete_code_snippet(id):
    snippet = CodeSnippet.query.get_or_404(id)
    db.session.delete(snippet)
    db.session.commit()
    flash("Code snippet deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- Contact Inquiries Management ---
@app.route("/admin/inquiry/update/<int:id>", methods=["POST"])
@admin_required
def update_inquiry_status(id):
    inquiry = ContactInquiry.query.get_or_404(id)
    status = request.form.get("status")
    inquiry.status = status
    db.session.commit()
    flash("Inquiry status updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/inquiry/delete/<int:id>", methods=["POST"])
@admin_required
def delete_inquiry(id):
    inquiry = ContactInquiry.query.get_or_404(id)
    db.session.delete(inquiry)
    db.session.commit()
    flash("Inquiry deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# --- GitHub Stats Update ---
@app.route("/admin/github/update", methods=["POST"])
@admin_required
def manual_github_update():
    try:
        update_github_stats()
        flash("GitHub stats updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating GitHub stats: {e}", "danger")
    return redirect(url_for("admin_dashboard"))

def update_github_stats():
    """Update GitHub statistics from API"""
    username = "vishaldeshmukh2k6"  # Your GitHub username
    
    try:
        # Set timeout and headers for security
        headers = {'User-Agent': 'Portfolio-Website/1.0'}
        timeout = 10
        
        # Get user info
        user_response = requests.get(
            f"https://api.github.com/users/{username}", 
            headers=headers, 
            timeout=timeout
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Get repositories
        repos_response = requests.get(
            f"https://api.github.com/users/{username}/repos?per_page=100", 
            headers=headers, 
            timeout=timeout
        )
        repos_response.raise_for_status()
        repos_data = repos_response.json()
        
        # Validate response data
        if not isinstance(repos_data, list):
            raise ValueError("Invalid repository data received")
        
        # Calculate stats
        total_stars = sum(repo.get('stargazers_count', 0) for repo in repos_data if isinstance(repo, dict))
        total_forks = sum(repo.get('forks_count', 0) for repo in repos_data if isinstance(repo, dict))
        
        # Get most used language
        languages = defaultdict(int)
        for repo in repos_data:
            if isinstance(repo, dict) and repo.get('language'):
                languages[repo['language']] += 1
        most_used_language = max(languages.items(), key=lambda x: x[1])[0] if languages else "Python"
        
        # Update or create stats record
        stats = GitHubStats.query.first()
        if stats:
            stats.public_repos = user_data.get('public_repos', 0)
            stats.followers = user_data.get('followers', 0)
            stats.following = user_data.get('following', 0)
            stats.total_stars = total_stars
            stats.total_forks = total_forks
            stats.most_used_language = most_used_language
            stats.last_updated = datetime.utcnow()
        else:
            stats = GitHubStats(
                username=username,
                public_repos=user_data.get('public_repos', 0),
                followers=user_data.get('followers', 0),
                following=user_data.get('following', 0),
                total_stars=total_stars,
                total_forks=total_forks,
                most_used_language=most_used_language
            )
            db.session.add(stats)
        
        db.session.commit()
        
    except Exception as e:
        app.logger.error(f"Error updating GitHub stats: {e}")
        # Create default stats if API fails
        if not GitHubStats.query.first():
            default_stats = GitHubStats(
                username=username,
                public_repos=15,
                followers=10,
                following=20,
                total_stars=50,
                total_forks=25,
                most_used_language="Python"
            )
            db.session.add(default_stats)
            db.session.commit()

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    app.logger.error(f"Server error: {e}")
    return render_template("errors/500.html"), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": "Too many requests"}), 429

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden"}), 403

@app.errorhandler(400)
def handle_csrf_error(e):
    if 'CSRF' in str(e):
        flash("Security token expired. Please try again.", "danger")
        return redirect(request.referrer or url_for('home'))
    return jsonify({"error": "Bad request"}), 400






# --- Main ---
def initialize_app():
    """Initialize application data"""
    try:
        with app.app_context():
            # Create all database tables
            db.create_all()
            print("Database tables created successfully")
            
            # Create upload directory
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                print("Upload directory created")
            except Exception as e:
                print(f"Upload directory error: {e}")
            
            # Initialize default skills if none exist
            try:
                if not Skill.query.first():
                    default_skills = [
                        Skill(name="Python", category="Backend", proficiency=95, years_experience=3.5),
                        Skill(name="Flask", category="Backend", proficiency=90, years_experience=3.0),
                        Skill(name="JavaScript", category="Frontend", proficiency=80, years_experience=2.5),
                        Skill(name="React", category="Frontend", proficiency=75, years_experience=1.5),
                        Skill(name="MySQL", category="Database", proficiency=85, years_experience=3.0),
                        Skill(name="Docker", category="DevOps", proficiency=70, years_experience=1.0),
                        Skill(name="AWS", category="Cloud", proficiency=75, years_experience=1.5),
                        Skill(name="Git", category="Tools", proficiency=90, years_experience=3.0)
                    ]
                    for skill in default_skills:
                        db.session.add(skill)
                    db.session.commit()
                    print("Default skills added")
            except Exception as e:
                print(f"Skills initialization error: {e}")
                db.session.rollback()
            
            # Initialize GitHub stats (optional)
            try:
                update_github_stats()
                print("GitHub stats updated")
            except Exception as e:
                print(f"GitHub stats error (ignored): {e}")
                
    except Exception as e:
        print(f"App initialization error: {e}")
        raise

# Initialize app for both development and production
try:
    initialize_app()
except Exception as e:
    print(f"Initialization error: {e}")
    # Continue anyway for basic functionality

if __name__ == "__main__":
    # Development server only
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(debug=False, host=host, port=port)
