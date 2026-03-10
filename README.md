
# Makaohub

## Setup Instructions

### Prerequisites
- Python 3.9+
- pip
- virtualenv

### Installation

1. **Clone the repository**
    ```bash
    git clone <repository-url>
    cd Makaohub
    ```

2. **Create virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment variables**
    ```bash
    cp .env.example .env
    # Edit .env with your settings
    ```

5. **Run migrations**
    ```bash
    python manage.py migrate
    ```

6. **Create superuser**
    ```bash
    python manage.py createsuperuser
    ```

### Running Locally

```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

## Deployment

### Production Setup

1. **Install production dependencies**
    ```bash
    pip install -r requirements-prod.txt
    ```

2. **Collect static files**
    ```bash
    python manage.py collectstatic --noinput
    ```

3. **Run migrations**
    ```bash
    python manage.py migrate --noinput
    ```

4. **Configure settings**
    - Set `DEBUG = False`
    - Update `ALLOWED_HOSTS`
    - Configure database credentials
    - Set secure cookie settings

5. **Deploy using gunicorn**
    ```bash
    gunicorn config.wsgi:application --bind 0.0.0.0:8000
    ```
