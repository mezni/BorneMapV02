#!/bin/bash
set -e

# ----------------------------
# Environment variables
# ----------------------------
PGHOST=${PGHOST:-postgis}
PGPORT=${PGPORT:-5432}
PGUSER=${PGUSER:-postgres}
PGPASSWORD=${PGPASSWORD:-password}
PGDATABASE=${PGDATABASE:-ev_db}
REGION=${REGION:-tunisia}
DATADIR=${DATADIR:-/osm/data}
PBF=${PBF:-$DATADIR/${REGION}-latest.osm.pbf}
STYLE=${STYLE:-/usr/local/bin/custom.style}
HOST=download.geofabrik.de

echo "📌 Starting OSM import for region: $REGION"
echo "Data directory: $DATADIR"
echo "PBF file: $PBF"

# ----------------------------
# Wait for PostGIS to be ready
# ----------------------------
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" > /dev/null 2>&1; do
  echo "⏳ Waiting for PostGIS to be ready..."
  sleep 3
done

# ----------------------------
# Ensure database extensions
# ----------------------------
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "CREATE EXTENSION IF NOT EXISTS hstore;"

# ----------------------------
# Download PBF if missing
# ----------------------------
if [[ ! -f "$PBF" ]]; then
  echo "🌐 Downloading $REGION OSM PBF from Geofabrik..."
  mkdir -p "$DATADIR"
  curl -L -o "$PBF" "https://${HOST}/${REGION}-latest.osm.pbf"
else
  echo "✅ Found local PBF at $PBF"
fi

# ----------------------------
# Check if database is already imported
# ----------------------------
if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "SELECT 1 FROM osm2pgsql_properties LIMIT 1;" > /dev/null 2>&1; then
  echo "🔄 Updating existing database with replication..."
  osm2pgsql-replication update \
    -v \
    --host "$PGHOST" \
    --database "$PGDATABASE" \
    --username "$PGUSER" \
    --port "$PGPORT" \
    -- -k --style "$STYLE" --extra-attributes
else
  echo "🚀 Performing fresh import with osm2pgsql..."

  osm2pgsql -v \
    --create \
    --slim \
    --cache 4000 \
    --hstore \
    --style "$STYLE" \
    --host "$PGHOST" \
    --database "$PGDATABASE" \
    --user "$PGUSER" \
    --port "$PGPORT" \
    "$PBF"  

  echo "✅ Import complete. Initializing replication..."
  osm2pgsql-replication init \
    --host "$PGHOST" \
    --database "$PGDATABASE" \
    --user "$PGUSER" \
    --port "$PGPORT" \
    --osm-file "$PBF"
fi

echo "🎉 OSM import finished successfully."