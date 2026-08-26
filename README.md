# Australian Autism Knowledge Hub

Australian Autism Knowledge Hub is developed by ACAMI (Australian Centre for AI in Medical Innovation) at La Trobe University..


# set up working environment

git clone git@github.com:acami-ltu/australia-autism-knowledge-hub.git
python -m venv australia-autism-knowledge-hub\env
source australia-autism-knowledge-hub/env/bin/activate
pip install wagtail

# set up local PostgreSQL

podman run -d --name aakh-pg \
  -e POSTGRES_DB=... -e POSTGRES_USER=... -e POSTGRES_PASSWORD=... \
  -p 55432:5432 \
  -v /home/ad/plai/aakh-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16


  podman start aakh-pg
  