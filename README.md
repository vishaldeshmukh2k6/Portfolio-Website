# Portfolio Website

A modern, feature-rich portfolio website built with Flask, featuring a blog, code snippets, project showcase, and admin dashboard.

## Features

- 🎨 Modern responsive design
- 📝 Blog system with tags and search
- 💻 Code snippets showcase
- 📊 Admin dashboard for content management
- 📧 Contact form with email notifications
- 🔒 Secure authentication and CSRF protection
- 📈 Visitor analytics and GitHub stats integration
- 🎯 Rate limiting and security headers
- 📱 Mobile-friendly interface

## Tech Stack

- **Backend:** Flask 2.3.3
- **Database:** SQLite
- **Security:** Flask-Talisman, Flask-WTF, Flask-Limiter
- **Email:** Flask-Mail
- **Production Server:** Gunicorn

## Local Development Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Portfolio-Website
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env  # Or create manually
```

5. Configure environment variables in `.env`:
```
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
ADMIN_USER=admin
ADMIN_PASS=secure-password
SECRET_KEY=your-secret-key
```

6. Initialize database:
```bash
python
>>> from app import initialize_app
>>> initialize_app()
>>> exit()
```

7. Run development server:
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Deployment

### PythonAnywhere Deployment

See [PYTHONANYWHERE_SETUP.md](PYTHONANYWHERE_SETUP.md) for detailed deployment instructions.

Quick steps:
1. Upload files to PythonAnywhere
2. Create virtual environment and install dependencies
3. Configure WSGI file
4. Set up static files mapping
5. Initialize database
6. Reload web app

### Docker Deployment

Build and run with Docker:
```bash
docker build -t portfolio-website .
docker run -p 5000:5000 --env-file .env portfolio-website
```

Or use Docker Compose:
```bash
docker-compose up -d
```

## Project Structure

```
Portfolio-Website/
├── app.py                  # Main application file
├── config.py              # Configuration settings
├── wsgi.py                # WSGI entry point for production
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── static/               # Static files (CSS, JS, images)
│   ├── uploads/          # User uploaded files
│   ├── certificates/     # Certificate PDFs
│   └── resume.pdf        # Resume file
├── templates/            # HTML templates
│   ├── errors/          # Error pages
│   ├── index.html       # Homepage
│   ├── admin.html       # Admin dashboard
│   ├── blog.html        # Blog listing
│   ├── blog_post.html   # Single blog post
│   └── ...
├── instance/            # Instance-specific files
│   └── portfolio.db     # SQLite database
└── Dockerfile           # Docker configuration
```

## Admin Dashboard

Access the admin dashboard at `/login` with credentials from `.env`:
- Username: Value of `ADMIN_USER`
- Password: Value of `ADMIN_PASS`

Admin features:
- Manage projects, blog posts, and code snippets
- View contact inquiries and visitor logs
- Update skills and certificates
- Monitor GitHub statistics
- View analytics

## API Endpoints

- `GET /api/projects` - List all projects
- `GET /api/skills` - Get skills by category
- `GET /api/github-stats` - GitHub statistics
- `GET /health` - Health check endpoint

## Security Features

- CSRF protection on all forms
- Rate limiting on sensitive endpoints
- Content Security Policy headers
- XSS protection
- Secure session cookies
- Input sanitization
- SQL injection prevention (SQLAlchemy ORM)

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key for sessions | Yes |
| `ADMIN_USER` | Admin username | Yes |
| `ADMIN_PASS` | Admin password | Yes |
| `MAIL_USERNAME` | Email for sending messages | Yes |
| `MAIL_PASSWORD` | Email app password | Yes |
| `GITHUB_USERNAME` | GitHub username for stats | No |
| `GITHUB_TOKEN` | GitHub API token (optional) | No |

## Database Models

- **Project** - Portfolio projects
- **BlogPost** - Blog articles
- **CodeSnippet** - Code examples
- **Skill** - Technical skills
- **Certificate** - Certifications
- **ContactInquiry** - Contact form submissions
- **VisitorLog** - Analytics data
- **GitHubStats** - GitHub statistics cache

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Contact via the website contact form

## Acknowledgments

- Flask framework and extensions
- Tailwind CSS for styling
- Font Awesome for icons
