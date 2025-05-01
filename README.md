# Klarro Backend

A Django-based backend for the Klarro interview management system. Built with Django REST Framework, PostgreSQL, and Celery.

## Features

- 🔐 Authentication & Authorization
  - Token-based authentication
  - Role-based access control
  - User management

- 📊 Interview Flow Management
  - CRUD operations for interview flows
  - Step management and ordering
  - Flow status tracking
  - Role-based flow categorization

- 👥 Candidate Management
  - Candidate profile management
  - Interview progress tracking
  - Bulk candidate import
  - Resume handling

- 🤖 AI Integration
  - Interview question generation
  - Candidate evaluation
  - Automated feedback
  - Skill assessment

## Tech Stack

- **Framework**: Django 4.x
- **API**: Django REST Framework
- **Database**: PostgreSQL
- **Task Queue**: Celery
- **Cache**: Redis
- **Authentication**: Token-based
- **Documentation**: Swagger/OpenAPI

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Node.js 16+ (for frontend)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/klarro.git
   cd klarro/backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

8. Start Celery worker (in a separate terminal):
   ```bash
   celery -A klarro worker -l info
   ```

The API will be available at `http://localhost:8000/api/v1`.

## Project Structure

```
backend/
├── klarro/           # Main project directory
├── interviews/        # Interview management app
├── candidates/        # Candidate management app
├── users/            # User management app
├── core/             # Core functionality
└── utils/            # Utility functions
```

## API Documentation

API documentation is available at `/api/docs/` when running the server.

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions and classes
- Implement proper error handling
- Write unit tests for new features

### Available Commands

- `python manage.py runserver` - Start development server
- `python manage.py test` - Run tests
- `python manage.py makemigrations` - Create migrations
- `python manage.py migrate` - Apply migrations
- `python manage.py shell` - Open Django shell
- `python manage.py createsuperuser` - Create admin user

### Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test interviews

# Run with coverage
coverage run manage.py test
coverage report
```

## Deployment

1. Set up production environment variables
2. Configure production database
3. Run migrations
4. Collect static files
5. Set up Gunicorn
6. Configure Nginx
7. Set up SSL certificates

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Write tests
4. Run linting and tests
5. Submit a pull request

## License

[MIT License](LICENSE)
