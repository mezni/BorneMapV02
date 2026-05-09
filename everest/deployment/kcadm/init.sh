#!/bin/bash
set -euo pipefail

########################################
# Configuration (env overridable)
########################################
KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-password}"
REALM="${KEYCLOAK_REALM:-myrealm}"

FRONTEND_CLIENT_ID="${FRONTEND_CLIENT_ID:-auth-client}"
BACKEND_CLIENT_ID="${BACKEND_CLIENT_ID:-backend-admin}"
BACKEND_CLIENT_SECRET="${BACKEND_CLIENT_SECRET:-backend-admin-secret}"

KCADM="/opt/keycloak/bin/kcadm.sh"
LOGIN_FLAGS="--server $KEYCLOAK_URL --realm master --user $ADMIN_USER --password $ADMIN_PASS"

########################################
# Helpers
########################################
log() { echo "[$(date +'%H:%M:%S')] $*"; }

kc() { $KCADM "$@" $LOGIN_FLAGS; }

get_client_uuid() {
  kc get clients -r "$REALM" -q clientId="$1" --fields id --format csv \
    | tail -n1 | tr -d '"'
}

get_service_account_user() {
  kc get clients/"$1"/service-account-user -r "$REALM" --fields id --format csv \
    | tail -n1 | tr -d '"'
}

########################################
# Wait for Keycloak
########################################
log "Waiting for Keycloak..."
for _ in {1..60}; do
  kc get realms/master >/dev/null 2>&1 && break
  sleep 5
done
log "Keycloak is ready"

########################################
# Realm
########################################
if ! kc get realms/"$REALM" >/dev/null 2>&1; then
  log "Creating realm $REALM"
  kc create realms \
    -s realm="$REALM" \
    -s enabled=true \
    -s attributes.userProfileEnabled=true
else
  log "Realm $REALM already exists"
fi

########################################
# Enable unmanaged attributes
########################################
log "Enabling unmanaged attributes"
kc update realms/"$REALM"/users/profile \
  -r "$REALM" \
  -f - <<EOF
{
  "unmanagedAttributePolicy": "ENABLED"
}
EOF

########################################
# Realm Roles
########################################
log "Creating realm roles"

for ROLE in admin user operator partner; do
  if kc get roles/"$ROLE" -r "$REALM" >/dev/null 2>&1; then
    log "Role already exists: $ROLE"
  else
    kc create roles -r "$REALM" -s name="$ROLE"
    log "Created role: $ROLE"
  fi
done


########################################
# Clients
########################################
log "Configuring frontend client"
kc get clients -r "$REALM" -q clientId="$FRONTEND_CLIENT_ID" | grep -q id || \
kc create clients -r "$REALM" \
  -s clientId="$FRONTEND_CLIENT_ID" \
  -s protocol=openid-connect \
  -s publicClient=true \
  -s standardFlowEnabled=true \
  -s directAccessGrantsEnabled=true \
  -s redirectUris='["http://localhost:8081/*"]' \
  -s webOrigins='["http://localhost:8081"]'

log "Configuring backend client"
kc get clients -r "$REALM" -q clientId="$BACKEND_CLIENT_ID" | grep -q id || \
kc create clients -r "$REALM" \
  -s clientId="$BACKEND_CLIENT_ID" \
  -s protocol=openid-connect \
  -s publicClient=false \
  -s secret="$BACKEND_CLIENT_SECRET" \
  -s serviceAccountsEnabled=true

########################################
# Ensure service account enabled
########################################
BACKEND_UUID=$(get_client_uuid "$BACKEND_CLIENT_ID")
kc update clients/"$BACKEND_UUID" -r "$REALM" -s serviceAccountsEnabled=true

########################################
# Protocol mappers (Frontend)
########################################
FRONTEND_UUID=$(get_client_uuid "$FRONTEND_CLIENT_ID")

create_mapper() {
  kc create clients/"$FRONTEND_UUID"/protocol-mappers/models -r "$REALM" -f -
}

create_mapper <<EOF
{
  "name": "realm-roles-mapper",
  "protocol": "openid-connect",
  "protocolMapper": "oidc-usermodel-realm-role-mapper",
  "config": {
    "multivalued": "true",
    "userinfo.token.claim": "true",
    "user.attribute": "roles",
    "id.token.claim": "true",
    "access.token.claim": "true",
    "claim.name": "roles",
    "jsonType.label": "String"
  }
}
EOF

for ATTR in network_id station_id; do
create_mapper <<EOF
{
  "name":"$ATTR",
  "protocol":"openid-connect",
  "protocolMapper":"oidc-usermodel-attribute-mapper",
  "config":{
    "user.attribute":"$ATTR",
    "claim.name":"$ATTR",
    "access.token.claim":"true",
    "id.token.claim":"true",
    "userinfo.token.claim":"true"
  }
}
EOF
done

########################################
# Service Account Roles (Backend Admin)
########################################
log "Assigning realm-management roles"

SERVICE_USER_UUID=$(get_service_account_user "$BACKEND_UUID")

if [[ -z "$SERVICE_USER_UUID" ]]; then
  log "ERROR: Service account user not found"
  exit 1
fi

ADMIN_ROLES=(
  manage-users
  view-users
  query-users
  view-realm
  manage-realm
  manage-clients
  view-clients
  query-clients
)

for ROLE in "${ADMIN_ROLES[@]}"; do
  kc add-roles \
    -r "$REALM" \
    --uid "$SERVICE_USER_UUID" \
    --cclientid realm-management \
    --rolename "$ROLE" \
    >/dev/null 2>&1 || true
  log "Assigned realm-management role: $ROLE"
done

log "Keycloak bootstrap completed successfully"

########################################
# Audience Mapper (Fixes InvalidAudience)
########################################
log "Adding audience mapper to frontend client"

create_mapper <<EOF
{
  "name": "audience-mapper",
  "protocol": "openid-connect",
  "protocolMapper": "oidc-audience-mapper",
  "config": {
    "included.client.audience": "$FRONTEND_CLIENT_ID",
    "id.token.claim": "false",
    "access.token.claim": "true"
  }
}
EOF


########################################
# Create Initial Admin User
########################################
ADMIN_USERNAME="system"
ADMIN_EMAIL="system@example.com"
ADMIN_PASSWORD="password"

log "Checking for initial system user: $ADMIN_USERNAME"

# 1. Check if user exists, if not create them
USER_EXISTS=$(kc get users -r "$REALM" -q username="$ADMIN_USERNAME" --fields id --format csv | tail -n1)

if [[ -z "$USER_EXISTS" || "$USER_EXISTS" == "id" ]]; then
  log "Creating system user..."
  
  # Create the user
  kc create users -r "$REALM" \
    -s username="$ADMIN_USERNAME" \
    -s email="$ADMIN_EMAIL" \
    -s enabled=true \
    -s emailVerified=true
  
  # 2. Set the password
  kc set-password -r "$REALM" \
    --username "$ADMIN_USERNAME" \
    --new-password "$ADMIN_PASSWORD" \
    
  # 3. Assign the 'admin' realm role
  kc add-roles -r "$REALM" \
    --uusername "$ADMIN_USERNAME" \
    --rolename admin
    
    
  log "System user created and 'admin' role assigned."
else
  log "System user already exists."
fi