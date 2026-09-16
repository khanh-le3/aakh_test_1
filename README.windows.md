# Australian Autism Knowledge Hub
The application runs on Wagtail 7.4, Django 5.2, and PostgreSQL 16. Python
dependencies are pinned in [requirements.lock](requirements.lock).

## 1. Prerequisites
This guide is for **Windows PowerShell**, using Python on Windows and PostgreSQL
in a **rootless Podman** container backed by **WSL 2**. Podman Desktop is optional;
the Podman command-line tool is enough.

Install Git for Windows, Python 3.12, and the
[Podman Windows installer](https://podman.io/docs/installation). Choose WSL 2
as the provider. Restart your IDE after installation so its terminal picks up
the updated PATH.

If WSL is not installed, run this in PowerShell as administrator, then restart Windows:

```powershell
wsl --install --no-distribution
```

Update WSL and check the tools in a new PowerShell terminal:

```powershell
wsl --update
wsl --version
git --version
py -3.12 --version
podman --version
podman machine list
```

If no Podman machine exists, create it once:

```powershell
podman machine init
```

Start the machine if it is stopped, then verify the connection:

```powershell
podman machine start
podman info
```

Keep rootless mode for this project. Continue when `podman info` succeeds.
See the [Windows provider setup](https://podman-desktop.io/docs/installation/windows-install#installing-podman)
and [Microsoft WSL commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
for installation details.

## 2. Clone the repository and install Python dependencies

Skip cloning if you already have this repository; open PowerShell in its folder.

```powershell
git clone https://github.com/acami-ltu/australia-autism-knowledge-hub.git
cd australia-autism-knowledge-hub
```

Create a Windows virtual environment once, then install dependencies:

```powershell
py -3.12 -m venv env
.\env\Scripts\python.exe -m pip install --upgrade pip
.\env\Scripts\python.exe -m pip install -r requirements.lock
.\env\Scripts\python.exe -m pip check
```

If you use GitHub SSH authentication, replace the clone URL with
`git@github.com:acami-ltu/australia-autism-knowledge-hub.git`.

Run the remaining commands from the repository root (the folder containing
`manage.py`). These commands call the virtual environment's Python directly, so
activation and PowerShell execution-policy changes are unnecessary. If
`env\Scripts\python.exe` already exists, skip creating the environment. A Linux
virtual environment containing `env/bin/python` cannot be reused on Windows;
rename it before creating a Windows environment. Install
from `requirements.lock` for the pinned versions; [requirements.txt](requirements.txt)
records the direct dependency ranges. The frontend uses Django static files and
does not require an npm build.

## 3. Configure the local environment

For a new checkout, copy the example configuration (preserve an existing `.env`):

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Edit `.env` and replace `change-me` with your own local database password. Use a
password containing letters and numbers for the simple loader below. Keep each
setting on its own line, without inline comments. The database settings should be:

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

PowerShell does not support `source .env`. Load the `DB_*` settings like this:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*(DB_[A-Z_]+)\s*=(.*)$') {
        $name = $matches[1]
        $value = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "Env:$name" -Value $value
    }
}

foreach ($name in 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_PORT') {
    if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
        throw "Missing $name in .env. Fill it in before creating the container."
    }
}
```

This loader supports the simple `KEY=value` format above, with optional surrounding
quotes. It does not implement shell expansion or inline comments. Run it again
after editing `.env` or opening a new terminal if you need variables for Podman.
PowerShell refers to environment variables as `$env:DB_NAME`, not `$DB_NAME`.

Run these commands in order, stopping if a command fails. Paste the entire
`podman run` command as one line; PowerShell does not use `\` for line continuation.

```powershell
podman pull docker.io/library/postgres:16
podman volume create aakh-pgdata
podman run -d --name aakh-pg -e "POSTGRES_DB=$env:DB_NAME" -e "POSTGRES_USER=$env:DB_USER" -e "POSTGRES_PASSWORD=$env:DB_PASSWORD" -p "127.0.0.1:${env:DB_PORT}:5432" -v aakh-pgdata:/var/lib/postgresql/data docker.io/library/postgres:16
```

The database is reachable locally on port DB_PORT; PostgreSQL listens on `5432`
inside the container. 

Check readiness before running migrations:

```powershell
podman exec aakh-pg pg_isready -U "$env:DB_USER" -d "$env:DB_NAME"
```

Wait until this reports `accepting connections`; rerun it after a few seconds if
initialisation is still in progress. If the container exits or remains unavailable,
inspect its logs:

```powershell
podman logs aakh-pg
```

Readiness only checks whether PostgreSQL accepts connections. Verify that Django
can actually authenticate with your configured database settings:

```powershell
.\env\Scripts\python.exe manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection successful')"
```

Continue when it prints `Database connection successful`. Existing `$env:DB_*`
variables override `.env`. If you changed `.env`, reload it above or use a fresh
terminal with no exported database variables before running this check.

## 5. Initialise Django and start the site

```powershell
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py runserver
```

Follow the prompts to create your own administrator account. Open:

- Website: <http://localhost:8000/>
- Wagtail admin: <http://localhost:8000/admin/>
- Knowledge library frontend preview: <http://localhost:8000/knowledge-library/>

Migrations create the initial homepage and default Wagtail site. They also populate
the homepage hero with the starter heading and introduction from `home/models.py`
and link “Explore the library” to the knowledge library. Run `.\env\Scripts\python.exe manage.py migrate`
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

From the repository root, check the Podman machine:

```powershell
podman machine list
```

If it is stopped, run `podman machine start`. Then start the existing database:

```powershell
podman start aakh-pg
podman exec aakh-pg pg_isready
```

Wait for `accepting connections`, then verify credentials and start Django:

```powershell
.\env\Scripts\python.exe manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection successful')"
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py runserver
```

Wait for the readiness check to succeed before continuing. Use `podman start`
for an existing container; `podman run` is only needed when creating it.

After pulling changes, update dependencies and apply committed migrations:

```powershell
git pull
.\env\Scripts\python.exe -m pip install -r requirements.lock
.\env\Scripts\python.exe manage.py migrate
```

When you change models, generate and review migrations, then apply them:

```powershell
.\env\Scripts\python.exe manage.py makemigrations
.\env\Scripts\python.exe manage.py migrate
```

Run the project checks and tests with PostgreSQL running:

```powershell
.\env\Scripts\python.exe -m pip check
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py test
```

Django tests create a separate test database. The database user created by the
container setup has the required permissions.

To finish, stop the development server with `Ctrl+C`, then:

```powershell
podman stop aakh-pg
```

Stopping the container keeps the database volume. Optionally run
`podman machine stop` to stop the VM as well. No `deactivate` command is needed
because this guide uses Python directly without activating the environment.

## Troubleshooting

- **`py` or Python 3.12 not found:** install Python 3.12 with the Windows Python
  launcher, restart your IDE, and check `py -3.12 --version`.
- **`podman` not recognised:** install the Podman CLI and restart your IDE to
  refresh PATH. Podman Desktop is not required.
- **`source`, `-e`, or `-p` not recognised; invalid reference `\`:** use the
  PowerShell commands in this guide. Paste `podman run` as a single line and
  use plain underscores, such as `POSTGRES_DB`, without backslashes.
- **Repository access denied:** check your GitHub repository access and HTTPS or
  SSH authentication.
- **Missing Django or another Python module:** use `env\Scripts\python.exe` and rerun
  `.\env\Scripts\python.exe -m pip install -r requirements.lock`.
- **Missing `DB_NAME`, `DB_USER`, or `DB_PASSWORD`:** check that `.env` exists
  beside `manage.py` and contains the database settings above.
- **Connection refused:** use `podman ps -a`, `podman logs aakh-pg`, and the
  readiness command above. Check that `.env` uses the published host port and
  `DB_HOST=localhost`.
- **Database authentication failed:** make sure `.env` matches the credentials
  used when the volume was first initialised. Existing exported `DB_*` variables
  override `.env`; unset stale values before retrying.
- **Port `55432` already in use:** choose a free `DB_PORT` in `.env` before
  creating the container, then rerun the PowerShell loader in step 4. An existing container keeps
  its original port mapping.
- **Container name already exists:** inspect it with `podman ps -a` and use
  `podman start aakh-pg` to resume the existing database.
- **Port `8000` already in use:** run `.\env\Scripts\python.exe manage.py runserver 8001` and open
  `http://localhost:8001/`. Set `WAGTAILADMIN_BASE_URL=http://localhost:8001` in
  `.env` to match.

### Podman machine startup failure on Windows

The rootless-mode message is informational. An automatically reassigned SSH port
is not by itself a failure. A busy `docker_engine` pipe concerns Docker API
forwarding; use `podman info` to determine whether the Podman CLI can connect.
If startup ends with `machine did not transition into running state`, the machine
still needs troubleshooting.

Update WSL first:

```powershell
wsl --update
```

If updating through the Microsoft Store fails, try `wsl --update --web-download`.
After updating, save work in any WSL sessions: the next command stops all WSL
distributions, preserving their files.

```powershell
wsl --shutdown
podman machine start
podman info
```

This is a troubleshooting step, not a guaranteed fix. If startup still fails,
collect diagnostics:

```powershell
wsl --version
wsl --list --verbose
podman --version
podman --log-level=debug machine start
```

Do not reset or remove a machine containing database data without a backup.
Changing `.env` does not change credentials already stored in `aakh-pgdata`.

See [AGENTS.md](AGENTS.md) for the project's implementation and accessibility rules.
