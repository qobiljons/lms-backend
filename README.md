# LMS Backend API

A Django REST Framework backend for a Learning Management System with JWT authentication, role-based access control, and paginated endpoints.

## Tech Stack

- **Django 6.0** / **Django REST Framework**
- **SimpleJWT** for authentication
- **drf-yasg** for Swagger/OpenAPI docs
- **SQLite** (default, swappable)

## Getting Started

```bash
# Install dependencies
pip install -e .

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

## Swagger Documentation

Once the server is running, visit:

- **Swagger UI**: [http://localhost:8000/swagger/](http://localhost:8000/swagger/)
- **Schema (JSON)**: [http://localhost:8000/swagger.json](http://localhost:8000/swagger.json)
- **Schema (YAML)**: [http://localhost:8000/swagger.yaml](http://localhost:8000/swagger.yaml)

## Authentication

All endpoints (except signup, login, and token refresh) require a valid JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

## Pagination

List endpoints are paginated. Defaults:
- Users: **5 items per page** (supports `?page_size=` up to 50)
- Courses: **5 items per page** (supports `?page_size=` up to 50)
- Lessons: **8 items per page** (global default)

```json
{
  "count": 100,
  "next": "http://localhost:8000/courses/?page=2",
  "previous": null,
  "results": [...]
}
```

Navigate pages with `?page=N` query parameter.

---

## User Roles

| Role         | Description                              |
|--------------|------------------------------------------|
| `student`    | Default role. Read-only access to courses/lessons. |
| `instructor` | Read-only access to courses/lessons.     |
| `admin`      | Full CRUD on courses, lessons, and users.|

---

## API Endpoints

### Authentication

| Method | Endpoint                    | Auth     | Description                        |
|--------|-----------------------------|----------|------------------------------------|
| POST   | `/auth/signup/`             | None     | Register a new student account     |
| POST   | `/auth/login/`              | None     | Login and receive JWT tokens       |
| POST   | `/auth/logout/`             | Required | Blacklist a refresh token          |
| POST   | `/auth/token/refresh/`      | None     | Refresh an access token            |
| GET    | `/auth/me/`                 | Required | Get current user info + profile    |
| PATCH  | `/auth/me/`                 | Required | Update username, email, name       |
| GET    | `/auth/me/profile/`         | Required | Get current user profile           |
| PATCH  | `/auth/me/profile/`         | Required | Update phone, bio, avatar          |
| POST   | `/auth/me/change-password/` | Required | Change password                    |
| GET    | `/auth/dashboard/stats/`    | Admin    | Summary counts for users/courses/lessons |

#### POST `/auth/signup/`

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "is_active": true,
  "profile": {
    "phone": "",
    "avatar": null,
    "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
    "bio": ""
  },
  "tokens": {
    "refresh": "<refresh_token>",
    "access": "<access_token>"
  }
}
```

#### POST `/auth/login/`

**Request:**
```json
{
  "username": "johndoe",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "is_active": true,
  "profile": {
    "phone": "",
    "avatar": null,
    "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
    "bio": ""
  },
  "tokens": {
    "refresh": "<refresh_token>",
    "access": "<access_token>"
  }
}
```

#### POST `/auth/logout/`

**Request:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Response (200):**
```json
{
  "success": true
}
```

#### POST `/auth/token/refresh/`

**Request:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Response (200):**
```json
{
  "access": "<new_access_token>"
}
```

#### GET `/auth/me/`

**Response (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "profile": {
    "phone": "",
    "avatar": null,
    "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
    "bio": ""
  }
}
```

#### PATCH `/auth/me/`

Update your username, email, first name, or last name. All fields are optional.

**Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "newemail@example.com"
}
```

**Response (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "newemail@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "student",
  "profile": {
    "phone": "",
    "avatar": null,
    "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
    "bio": ""
  }
}
```

#### GET `/auth/me/profile/`

**Response (200):**
```json
{
  "phone": "+1234567890",
  "avatar": "http://localhost:8000/media/avatars/photo.png",
  "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
  "bio": "Hello world"
}
```

#### PATCH `/auth/me/profile/`

Update phone, bio, or avatar. Supports `multipart/form-data` for file uploads.

**Request (JSON):**
```json
{
  "phone": "+1234567890",
  "bio": "Software engineer"
}
```

**Request (multipart for avatar upload):**
```
Content-Type: multipart/form-data

avatar: <file>
```

**Response (200):**
```json
{
  "phone": "+1234567890",
  "avatar": "http://localhost:8000/media/avatars/photo.png",
  "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
  "bio": "Software engineer"
}
```

#### POST `/auth/me/change-password/`

**Request:**
```json
{
  "old_password": "currentpass123",
  "new_password": "newsecurepass123"
}
```

**Response (200):**
```json
{
  "detail": "password updated"
}
```

---

### Users (Admin Only)

| Method | Endpoint               | Auth        | Description                  |
|--------|------------------------|-------------|------------------------------|
| GET    | `/auth/users/`         | Admin       | List all users (paginated)   |
| POST   | `/auth/users/create/`  | Admin       | Create a new user account    |
| GET    | `/auth/users/<username>/` | Admin    | Get a user by username       |
| PATCH  | `/auth/users/<username>/` | Admin    | Update user fields/role      |
| DELETE | `/auth/users/<username>/` | Admin    | Delete a user                |
| POST   | `/auth/users/<username>/set-password/` | Admin | Set a user's password |

#### GET `/auth/users/`

Supports filtering and search:
- Filter: `?role=student|instructor|admin`, `?is_active=true|false`
- Search: `?search=john`
- Ordering: `?ordering=username|email|date_joined` (prefix with `-` for desc)

**Response (200):**
```json
{
  "count": 50,
  "next": "http://localhost:8000/auth/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "username": "johndoe",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "student",
      "is_active": true,
      "profile": {
        "phone": "",
        "avatar": null,
        "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=johndoe",
        "bio": ""
      }
    }
  ]
}
```

#### POST `/auth/users/create/`

Admin can create accounts with any role.

**Request:**
```json
{
  "email": "instructor@example.com",
  "username": "janedoe",
  "password": "securepass123",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "instructor"
}
```

`role` is optional and defaults to `"student"`. Accepted values: `student`, `instructor`, `admin`.

**Response (201):**
```json
{
  "id": 2,
  "username": "janedoe",
  "email": "instructor@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "instructor",
  "is_active": true,
  "profile": {
    "phone": "",
    "avatar": null,
    "default_avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=janedoe",
    "bio": ""
  }
}
```

---

### Courses

| Method | Endpoint               | Auth               | Description                   |
|--------|------------------------|--------------------|-------------------------------|
| GET    | `/courses/`            | Any authenticated  | List all courses (paginated)  |
| POST   | `/courses/`            | Admin              | Create a course               |
| GET    | `/courses/<slug>/`     | Any authenticated  | Get a course by slug          |
| PUT    | `/courses/<slug>/`     | Admin              | Full update a course          |
| PATCH  | `/courses/<slug>/`     | Admin              | Partial update a course       |
| DELETE | `/courses/<slug>/`     | Admin              | Delete a course               |

> Course titles must be **unique**.
> Course detail uses the course `slug` (read-only field).

#### GET `/courses/`

**Response (200):**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Django 101",
      "slug": "django-101",
      "description": "Learn Django from scratch",
      "logo": null,
      "created_at": "2026-02-08T17:00:00Z"
    }
  ]
}
```

#### POST `/courses/`

**Request:**
```json
{
  "title": "Django 101",
  "description": "Learn Django from scratch"
}
```

**Response (201):**
```json
{
  "id": 1,
  "title": "Django 101",
  "slug": "django-101",
  "description": "Learn Django from scratch",
  "logo": null,
  "created_at": "2026-02-08T17:00:00Z"
}
```

#### PUT `/courses/<id>/`

**Request:**
```json
{
  "title": "Django 201",
  "description": "Advanced Django"
}
```

#### PATCH `/courses/<id>/`

**Request:**
```json
{
  "title": "Django 201"
}
```

#### DELETE `/courses/<id>/`

**Response:** `204 No Content`

---

### Lessons

| Method | Endpoint               | Auth               | Description                   |
|--------|------------------------|--------------------|-------------------------------|
| GET    | `/lessons/`            | Any authenticated  | List all lessons (paginated)  |
| POST   | `/lessons/`            | Admin              | Create a lesson               |
| GET    | `/lessons/<id>/`       | Any authenticated  | Get a lesson by ID            |
| PUT    | `/lessons/<id>/`       | Admin              | Full update a lesson          |
| PATCH  | `/lessons/<id>/`       | Admin              | Partial update a lesson       |
| DELETE | `/lessons/<id>/`       | Admin              | Delete a lesson               |

Filtering is supported on list:
- `?course=<course_id>`
- `?user=<user_id>`

#### GET `/lessons/`

**Response (200):**
```json
{
  "count": 25,
  "next": "http://localhost:8000/lessons/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Introduction",
      "content": "Welcome to the course",
      "course": 1,
      "user": 1,
      "video_provider": "youtube",
      "youtube_url": "https://youtu.be/example",
      "homework": "",
      "created_at": "2026-02-08T17:00:00Z"
    }
  ]
}
```

#### POST `/lessons/`

**Request:**
```json
{
  "title": "Introduction",
  "content": "Welcome to the course",
  "course": 1,
  "user": 1,
  "video_provider": "youtube",
  "youtube_url": "https://youtu.be/example"
}
```

**Response (201):**
```json
{
  "id": 1,
  "title": "Introduction",
  "content": "Welcome to the course",
  "course": 1,
  "user": 1,
  "video_provider": "youtube",
  "youtube_url": "https://youtu.be/example",
  "homework": "",
  "created_at": "2026-02-08T17:00:00Z"
}
```

#### PUT `/lessons/<id>/`

**Request:**
```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "course": 1,
  "user": 1
}
```

#### PATCH `/lessons/<id>/`

**Request:**
```json
{
  "title": "Updated Title"
}
```

#### DELETE `/lessons/<id>/`

**Response:** `204 No Content`

---

## Error Responses

| Status | Description           |
|--------|-----------------------|
| 400    | Bad request / validation error |
| 401    | Unauthenticated       |
| 403    | Forbidden (insufficient role) |
| 404    | Resource not found    |

**Example error (400):**
```json
{
  "email": ["email already in use"]
}
```

**Example error (403):**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## Running Tests

```bash
python manage.py test apps.users apps.courses apps.lessons
```
