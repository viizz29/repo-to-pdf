# image classification based on face



## development setup
python3 -m venv .venv
and activate the venv
npm -r requirements.txt
create a postgres database
update the database details in the .env file

alembic upgrade headc
python app/seed_users.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
http://localhost:8000/docs


## production

This project uses Docker Compose to run both the API and a PostgreSQL database.

The default database connection in `.env` points the API container at the Compose database service:

```env
DATABASE_URL=postgresql://user:password@db:5432/app
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=app
```

Start the API:

```bash
docker compose up --build
```

To store uploads outside the repo, set these in `.env` before starting Compose:

```env
FACE_IMAGE_UPLOAD_DIR=/app/images
HOST_FACE_IMAGE_UPLOAD_DIR=/home/xyz/data/app/uploads
```

`HOST_FACE_IMAGE_UPLOAD_DIR` is the real host folder, and `FACE_IMAGE_UPLOAD_DIR` is the path the API uses inside the container. For a non-Docker local run, you can point `FACE_IMAGE_UPLOAD_DIR` directly at an absolute folder such as `/home/xyz/data/app/uploads`.

Apply database migrations after the containers are up:

```bash
docker compose exec api alembic upgrade head
```

If the Compose database already contains these tables from the earlier `create_all()` setup, mark the initial migration as applied instead:

```bash
docker compose exec api alembic stamp head
```

Create a new migration after changing SQLAlchemy models:

```bash
docker compose exec api alembic revision -m "describe change"
```

or

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
```

Seed default users:

```bash
docker compose exec api python app/seed_users.py
```

You can also run it as a module:

```bash
docker compose exec api python -m app.seed_users
```

# access the database using psql

docker compose exec db psql -U user -d app
