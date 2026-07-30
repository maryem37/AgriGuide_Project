# PostGIS (données géo) + pgvector (RAG légal), requis par database/schema.sql.
# L'image officielle postgis/postgis n'embarque pas pgvector — on l'ajoute
# depuis le dépôt PGDG déjà configuré dans l'image de base.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
