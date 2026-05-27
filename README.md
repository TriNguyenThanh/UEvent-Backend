# UEvent Backend - Event Management Engine

[](https://www.python.org/)
[](https://www.djangoproject.com/)
[](https://www.postgresql.org/)
[](https://opensource.org/licenses/MIT)

**UEvent Backend** is a robust API-driven core designed to power the UEvent ecosystem. Built with a focus on **Scalability, Security, and Clean Architecture**, it serves as the central nervous system for managing large-scale events, real-time interactions, and secure attendee validation.

> **Frontend (Flutter):** [Link to Repository](https://github.com/TriNguyenThanh/UEvent-Frontend-Flutter)

-----

## Business Value & Logic

UEvent addresses the complexity of modern event coordination by providing a seamless digital lifecycle:

  * **End-to-End Event Lifecycle:** From creation and role assignment (`Admin`, `Operator`, `Attendee`) to post-event feedback.
  * **Secure QR-Based Validation:** A proprietary check-in system using unique, encrypted QR codes to prevent unauthorized access.
  * **Dynamic Engagement:** Real-time Q\&A modules allowing participants to interact before, during, and after the event sessions.
  * **Data-Driven Feedback:** Integrated rating and review systems to measure event success and attendee satisfaction.

-----

## System Architecture

The project follows a **Hybrid (Feature-first) Monolithic Architecture**. This approach ensures high cohesion within features while maintaining low coupling between modules, making it "Microservice-ready."

### Tech Stack

  * **Core:** Django Rest Framework (DRF)
  * **Database:** PostgreSQL (Relational integrity for complex event schemas)
  * **API Standard:** RESTful with versioning (`/api/v1/`)
  * **Documentation:** Interactive **Swagger UI** & **Redoc**
  * **Security:** JWT-based stateless authentication

### Future-Proof Infrastructure (Roadmap)

  * **Caching Layer:** Redis implementation for high-traffic event lookups.
  * **Message Broker:** Apache Kafka for asynchronous notifications and audit logging.
  * **Auth Expansion:** Support for Passkeys (WebAuthn) and Social OAuth.

-----

## Engineering Excellence (DevOps)

  * **CI/CD Pipeline:** Powered by **GitHub Actions** to automate Linting (Flake8/Black) and Unit Testing.
  * **Quality Assurance:** High test coverage for critical business paths (Registration, Booking, Check-in).
  * **Environment Management:** Strict separation of concerns using `.env` for secrets and configuration.
  * **Seed Data:** Integrated fixtures for rapid development and staging deployment.

-----

## Getting Started

### Prerequisites

  * Python 3.10+
  * PostgreSQL Instance
  * Virtualenv / Pipenv

### Installation

1.  **Clone & Navigate**

    ```bash
    git clone https://github.com/TriNguyenThanh/UEvent-backend-Django.git
    cd UEvent-backend-Django
    ```

2.  **Environment Setup**

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Database Configuration**
    Create a `.env` file based on `.env.example`:

    ```env
    DB_NAME=uevent_db
    DB_USER=your_user
    DB_PASSWORD=your_password
    SECRET_KEY=your_django_secret
    ```

4.  **Migrate & Seed**

    ```bash
    python manage.py migrate
    python manage.py loaddata seed_data.json
    ```

5.  **Launch**

    ```bash
    python manage.py runserver
    ```

    Access the API Docs at: `http://localhost:8000/api/v1/swagger/`

### Push Notification Delivery

#### Backend Environment Variables & Secrets
Real push notification delivery uses Celery, Redis, and Firebase Cloud Messaging.

Required production variables:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
FCM_ENABLED=true
FCM_DRY_RUN=false
FIREBASE_CREDENTIALS_PATH=/run/firebase-service-account.json
FCM_BATCH_SIZE=500
FCM_MAX_RETRIES=3
FCM_DEVICE_TOKEN_TTL_DAYS=365
```

Required file secret:
`UEvent-Backend\firebase-service-account.json`

#### Frontend Mobile Environment Variables

`UEvent-Frontend\mobile\lib\firebase_options.dart`
`UEvent-Frontend\mobile\android\app\google-services.json`


Do not commit Firebase service account JSON. Mount it as a Docker secret or inject `FIREBASE_CREDENTIALS_JSON` from the deployment secret store.

-----

## Testing

To execute the automated test suite:

```bash
python manage.py test
```
