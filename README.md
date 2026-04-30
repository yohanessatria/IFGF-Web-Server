# IFGF Taipei Zhongli – Church Management API

FastAPI + PostgreSQL backend for managing church members, attendance, iCare groups, and ministries.

## Project Structure

```
church_api/
├── app/
│   ├── core/
│   │   ├── config.py        # Settings (reads .env)
│   │   ├── database.py      # SQLAlchemy engine & session
│   │   └── security.py      # JWT + password hashing
│   ├── models/
│   │   ├── user.py          # Auth user model
│   │   └── church.py        # All church models
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── routers/
│   │   ├── auth.py          # POST /api/auth/token, /register, /me
│   │   ├── members.py       # CRUD /api/members
│   │   ├── attendance.py    # Check-in + listing /api/attendance
│   │   ├── icare.py         # Groups & membership /api/icare
│   │   ├── ministries.py    # Ministry assignments /api/ministries
│   │   ├── dashboard.py     # Stats & analytics /api/dashboard
│   │   └── activity_types.py
│   └── main.py              # App entry point
├── seed_admin.py            # Creates first admin user
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL running locally

### 2. Create database
```sql
CREATE DATABASE ifgf_taipei;
```

Then run your schema + seed files:
```bash
psql -U postgres -d ifgf_taipei -f church_schema.sql
psql -U postgres -d ifgf_taipei -f church_dummy_data_fixed.sql
```

### 3. Install dependencies
```bash
cd church_api
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL and a strong SECRET_KEY
```

### 5. Create admin user
```bash
python seed_admin.py
```

### 6. Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs
Open your browser at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/token` | Login → get JWT token |
| POST | `/api/auth/register` | Register new user |
| GET  | `/api/auth/me` | Current user info |

### Members
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/members` | List members (filter by status, category, cgsl_status, search) |
| POST | `/api/members` | Create member |
| GET  | `/api/members/{id}` | Get member |
| PATCH | `/api/members/{id}` | Update member |
| DELETE | `/api/members/{id}` | Delete member |

### Attendance
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/attendance/checkin` | Check in a member |
| GET  | `/api/attendance` | List attendance (filter by date, activity, member) |
| GET  | `/api/attendance/session/{activity_type_id}/{date}` | All attendees for a session |
| DELETE | `/api/attendance/{id}` | Remove record |

### iCare
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/icare/groups` | List all groups |
| POST | `/api/icare/groups` | Create group |
| GET  | `/api/icare/groups/{id}/members` | List group members |
| POST | `/api/icare/members` | Add member to group |
| PATCH | `/api/icare/members/{id}/leave` | Mark member as left |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/dashboard/stats` | Overall church stats |
| GET  | `/api/dashboard/attendance/trends` | Weekly attendance trends |
| GET  | `/api/dashboard/members/new` | Recently joined members |
| GET  | `/api/dashboard/members/inactive-risk` | Active members not attending recently |

## Authentication
All endpoints (except login/register) require a Bearer token:
```
Authorization: Bearer <your_token>
```

Get a token via `POST /api/auth/token` with form fields `username` and `password`.

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/ifgf_taipei` | PostgreSQL connection string |
| `SECRET_KEY` | `change-this-in-production` | JWT signing secret |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token TTL |
