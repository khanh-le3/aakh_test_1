Project rules, in precedence order (higher wins on conflict):
- @rules/accessibility.md             required a11y features; OVERRIDES all layout and visual rules
- @rules/information_architecture.md  sitemap, page models, URLs
- @rules/code_conventions.md          CSS/JS/Python/template conventions
- @rules/design_system.md             Civic Theme + palette
- @rules/techstack.md                 Wagtail techstack constraints

Not a directive, but the evidence base — cite it when justifying a decision:
- @rules/references.md                WCAG, COGA, AU gov standards, autism research

## Commands
source env/bin/activate            # venv is ./env, pinned in .vscode/settings.json
pip install -r requirements.lock   # install from the LOCK file, never requirements.txt
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
podman start aakh-pg               # Postgres 16, host port 55432

## Layout
aakh/     project settings, base templates, static
home/     HomePage model + migrations
core/     navigation.py, templatetags (shared, no models)
search/   search view


- Wagtail 7.4 docs are vendored at `docs/vendor/wagtail-doc-llms-full.md` (60k lines). Always `grep` it — never read it whole.
