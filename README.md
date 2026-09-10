# Australian Autism Knowledge Hub
The application runs on Wagtail 7.4, Django 5.2, and PostgreSQL 16. Python
dependencies are pinned in [requirements.lock](requirements.lock).

## 1. Prerequisites
This guide uses **rootless Podman** as it is what is available on aiotcentre-01/02/03 servers.
Use Python 3.12 to match the existing development environment.

## 2. Clone the repository and install Python dependencies

```bash
git clone https://github.com/acami-ltu/australia-autism-knowledge-hub.git
cd australia-autism-knowledge-hub
python -m venv env
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip check
```

If you use GitHub SSH authentication, replace the clone URL with
`git@github.com:acami-ltu/australia-autism-knowledge-hub.git`.

Run the remaining commands from the repository root with `env` activated. Install
from `requirements.lock` for the pinned versions; [requirements.txt](requirements.txt)
records the direct dependency ranges. The frontend uses Django static files and
does not require an npm build.

## 3. Configure the local environment

For a new checkout, copy the example configuration (preserve an existing `.env`):

```bash
cp .env.example .env
```

Edit `.env` and replace `change-me` with your own local database password. Use a
password containing letters and numbers so the file can also be loaded by the
shell commands below. The database settings should be:

```dotenv
DB_NAME=aakh
DB_USER=admin
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=55432
```

Django automatically reads `.env` from the repository root. It is ignored by Git;
do not commit it. These instructions use `aakh.settings.dev`, the default in
`manage.py`. Local development already provides a development secret key and
prints emails to the terminal. The production-only settings in `.env.example`
can remain commented out.

## 4. Pull PostgreSQL and create the database container

Load your database settings into the current shell, download the PostgreSQL 16
image, and create a named volume to persist the database:

```bash
source .env
podman pull docker.io/library/postgres:16
podman volume create aakh-pgdata
podman run -d --name aakh-pg \
  -e POSTGRES_DB="$DB_NAME" \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  -p "127.0.0.1:${DB_PORT}:5432" \
  -v aakh-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16
```

The database is reachable locally on port DB_PORT; PostgreSQL listens on `5432`
inside the container. 

Check readiness before running migrations:

```bash
podman exec aakh-pg sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Wait until this reports `accepting connections`; rerun it after a few seconds if
initialisation is still in progress. If the container exits or remains unavailable,
inspect its logs:

```bash
podman logs aakh-pg
```

## 5. Initialise Django and start the site

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py runserver
```

Follow the prompts to create your own administrator account. Open:

- Website: <http://localhost:8000/>
- Wagtail admin: <http://localhost:8000/admin/>
- Knowledge library frontend preview: <http://localhost:8000/knowledge-library/>

Migrations create the initial homepage and default Wagtail site. They also populate
the homepage hero with the starter heading and introduction from `home/models.py`
and link “Explore the library” to the knowledge library. Run `python manage.py migrate`
on each deployment to apply this setup. The hero seed skips homepages with saved
Wagtail revisions and preserves existing copy and selected destinations. The
“About the Hub” button needs a destination selected in Wagtail before it appears.

The starter content is frozen in `home/migrations/0007_seed_hero_content.py`.
Changing model defaults alone does not update existing database rows; use a new
data migration for later starter-content changes. A fresh database does not
include another developer's editorial content or uploaded media. Edit
and publish the homepage through Wagtail to add content; reproducing an existing
site also requires its database and corresponding `media/` files. The knowledge
library currently has a development-only frontend preview.

The development server serves static assets automatically, so `collectstatic` is
not needed here. This setup is for local development only.

## Daily development

From the repository root, start an existing environment:

```bash
source env/bin/activate
podman start aakh-pg
podman exec aakh-pg sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
python manage.py migrate
python manage.py runserver
```

Wait for the readiness check to succeed before continuing. Use `podman start`
for an existing container; `podman run` is only needed when creating it.

After pulling changes, update dependencies and apply committed migrations:

```bash
git pull
python -m pip install -r requirements.lock
python manage.py migrate
```

When you change models, generate and review migrations, then apply them:

```bash
python manage.py makemigrations
python manage.py migrate
```

Run the project checks and tests with PostgreSQL running:

```bash
python -m pip check
python manage.py check
python manage.py test
```

Django tests create a separate test database. The database user created by the
container setup has the required permissions.

To finish, stop the development server with `Ctrl+C`, then:

```bash
podman stop aakh-pg
deactivate
```

Stopping the container keeps the database volume.

## Troubleshooting

- **Python 3.12 not found:** follow the user-level installation in step 1 and
  check that `$HOME/.local/bin` is on `PATH`.
- **`venv` or `ensurepip` unavailable:** your existing Python may be incomplete.
  Install Python through uv as shown above and use
  `"$HOME/.local/bin/python3.12" -m venv env` for the initial environment creation.
- **Podman fails with user namespace or UID/GID mapping errors:** ask the machine
  administrator to configure rootless Podman for your account using the guide
  in step 1. The remaining setup commands do not require sudo.
- **Repository access denied:** check your GitHub repository access and HTTPS or
  SSH authentication.
- **Missing Django or another Python module:** activate `env` and rerun
  `python -m pip install -r requirements.lock`.
- **Missing `DB_NAME`, `DB_USER`, or `DB_PASSWORD`:** check that `.env` exists
  beside `manage.py` and contains the database settings above.
- **Connection refused:** use `podman ps -a`, `podman logs aakh-pg`, and the
  readiness command above. Check that `.env` uses the published host port and
  `DB_HOST=localhost`.
- **Database authentication failed:** make sure `.env` matches the credentials
  used when the volume was first initialised. Existing exported `DB_*` variables
  override `.env`; unset stale values before retrying.
- **Port `55432` already in use:** choose a free `DB_PORT` in `.env` before
  creating the container, then rerun `source .env`. An existing container keeps
  its original port mapping.
- **Container name already exists:** inspect it with `podman ps -a` and use
  `podman start aakh-pg` to resume the existing database.
- **Port `8000` already in use:** run `python manage.py runserver 8001` and open
  `http://localhost:8001/`. Set `WAGTAILADMIN_BASE_URL=http://localhost:8001` in
  `.env` to match.

See [AGENTS.md](AGENTS.md) for the project's implementation and accessibility rules.
