-- Shree Krishna Steel / Chairvala — PostgreSQL setup (run as superuser postgres)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shreeramsteel') THEN
    CREATE ROLE shreeramsteel WITH LOGIN PASSWORD 'shreeramsteel';
  ELSE
    ALTER ROLE shreeramsteel WITH LOGIN PASSWORD 'shreeramsteel';
  END IF;
END
$$;

SELECT 'CREATE DATABASE shreeramsteel OWNER shreeramsteel'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shreeramsteel')\gexec

GRANT ALL PRIVILEGES ON DATABASE shreeramsteel TO shreeramsteel;
