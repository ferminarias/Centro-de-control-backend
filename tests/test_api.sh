#!/usr/bin/env bash
# =============================================================================
# Test completo de la API - Centro de Control
#
# Uso:
#   chmod +x tests/test_api.sh
#   ./tests/test_api.sh
#
# Variables de entorno opcionales:
#   BASE_URL    (default: http://localhost:8000)
#   ADMIN_KEY   (default: vacio, asume AUTH_ENABLED=false)
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_KEY="${ADMIN_KEY:-}"
PASS=0
FAIL=0

# --- Helpers -----------------------------------------------------------------

auth_header() {
  if [ -n "$ADMIN_KEY" ]; then
    echo "Authorization: Bearer $ADMIN_KEY"
  else
    echo "X-No-Auth: true"
  fi
}

check() {
  local test_name="$1"
  local expected_code="$2"
  local actual_code="$3"
  local body="$4"

  if [ "$actual_code" -eq "$expected_code" ]; then
    echo "  PASS  $test_name (HTTP $actual_code)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $test_name (esperado $expected_code, recibido $actual_code)"
    echo "        Body: $body"
    FAIL=$((FAIL + 1))
  fi
}

# Hace un request y captura code + body
do_request() {
  local method="$1"
  local url="$2"
  local data="${3:-}"

  if [ -n "$data" ]; then
    curl -s -w "\n%{http_code}" -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "$(auth_header)" \
      -d "$data"
  else
    curl -s -w "\n%{http_code}" -X "$method" "$url" \
      -H "$(auth_header)"
  fi
}

parse_response() {
  local response="$1"
  BODY=$(echo "$response" | sed '$d')
  CODE=$(echo "$response" | tail -1)
}

extract_json() {
  local json="$1"
  local field="$2"
  echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['$field'])" 2>/dev/null || echo ""
}

# =============================================================================
echo "============================================"
echo " Centro de Control - Test de API"
echo " Base URL: $BASE_URL"
echo "============================================"
echo ""

# --- 1. Health Check ---------------------------------------------------------
echo "[1] Health Check"
parse_response "$(do_request GET "$BASE_URL/health")"
check "GET /health" 200 "$CODE" "$BODY"
echo ""

# --- 2. Crear cuenta --------------------------------------------------------
echo "[2] Crear cuenta de prueba"
parse_response "$(do_request POST "$BASE_URL/api/v1/admin/accounts" '{
  "nombre": "Test Account API",
  "auto_crear_campos": true
}')"
check "POST /admin/accounts" 201 "$CODE" "$BODY"

ACCOUNT_ID=$(extract_json "$BODY" "id")
API_KEY=$(extract_json "$BODY" "api_key")
echo "    Account ID: $ACCOUNT_ID"
echo "    API Key:    $API_KEY"
echo ""

# --- 3. Listar cuentas ------------------------------------------------------
echo "[3] Listar cuentas"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts")"
check "GET /admin/accounts" 200 "$CODE" "$BODY"
echo ""

# --- 4. Detalle cuenta ------------------------------------------------------
echo "[4] Detalle de cuenta"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID")"
check "GET /admin/accounts/{id}" 200 "$CODE" "$BODY"
echo ""

# --- 5. Actualizar cuenta ---------------------------------------------------
echo "[5] Actualizar cuenta"
parse_response "$(do_request PUT "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID" '{
  "nombre": "Test Account Renombrada"
}')"
check "PUT /admin/accounts/{id}" 200 "$CODE" "$BODY"
echo ""

# --- 6. Toggle auto-crear campos --------------------------------------------
echo "[6] Toggle auto-crear campos"
parse_response "$(do_request PATCH "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/toggle-auto-create")"
check "PATCH toggle-auto-create" 200 "$CODE" "$BODY"
# Volver a activarlo para el test de ingest
do_request PATCH "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/toggle-auto-create" > /dev/null
echo ""

# --- 7. Crear campo manualmente ---------------------------------------------
echo "[7] Crear campo manualmente"
parse_response "$(do_request POST "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/fields" '{
  "nombre_campo": "test_manual",
  "tipo_dato": "string",
  "descripcion": "Campo creado por test",
  "es_requerido": false
}')"
check "POST /admin/accounts/{id}/fields" 201 "$CODE" "$BODY"

FIELD_ID=$(extract_json "$BODY" "id")
echo "    Field ID: $FIELD_ID"
echo ""

# --- 8. Listar campos -------------------------------------------------------
echo "[8] Listar campos"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/fields")"
check "GET /admin/accounts/{id}/fields" 200 "$CODE" "$BODY"
echo ""

# --- 9. Actualizar campo ----------------------------------------------------
echo "[9] Actualizar campo"
parse_response "$(do_request PUT "$BASE_URL/api/v1/admin/fields/$FIELD_ID" '{
  "descripcion": "Campo actualizado por test"
}')"
check "PUT /admin/fields/{id}" 200 "$CODE" "$BODY"
echo ""

# --- 10. Ingest webhook (crea Record + Lead) --------------------------------
echo "[10] Ingest webhook (POST)"
parse_response "$(do_request POST "$BASE_URL/api/v1/ingest/$API_KEY" '{
  "nombre": "Juan Perez",
  "email": "juan@example.com",
  "telefono": "+5491155551234",
  "empresa": "ACME Corp"
}')"
check "POST /ingest/{api_key}" 200 "$CODE" "$BODY"

RECORD_ID=$(extract_json "$BODY" "record_id")
LEAD_ID=$(extract_json "$BODY" "lead_id")
echo "    Record ID: $RECORD_ID"
echo "    Lead ID:   $LEAD_ID"
echo ""

# --- 11. Verificar que lead_id viene en la respuesta -------------------------
echo "[11] Verificar lead_id en respuesta de ingest"
if [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "" ]; then
  echo "  PASS  lead_id presente en IngestResponse"
  PASS=$((PASS + 1))
else
  echo "  FAIL  lead_id NO presente en IngestResponse"
  FAIL=$((FAIL + 1))
fi
echo ""

# --- 12. Listar records -----------------------------------------------------
echo "[12] Listar records"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/records")"
check "GET /admin/accounts/{id}/records" 200 "$CODE" "$BODY"
echo ""

# --- 13. Detalle record -----------------------------------------------------
echo "[13] Detalle de record"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/records/$RECORD_ID")"
check "GET /admin/records/{id}" 200 "$CODE" "$BODY"
echo ""

# --- 14. Listar leads -------------------------------------------------------
echo "[14] Listar leads"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/leads")"
check "GET /admin/accounts/{id}/leads" 200 "$CODE" "$BODY"

LEADS_TOTAL=$(extract_json "$BODY" "total")
echo "    Total leads: $LEADS_TOTAL"
echo ""

# --- 15. Detalle lead -------------------------------------------------------
echo "[15] Detalle de lead"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/leads/$LEAD_ID")"
check "GET /admin/leads/{id}" 200 "$CODE" "$BODY"
echo ""

# --- 16. Segundo ingest para verificar paginacion ---------------------------
echo "[16] Segundo ingest"
parse_response "$(do_request POST "$BASE_URL/api/v1/ingest/$API_KEY" '{
  "nombre": "Maria Lopez",
  "email": "maria@example.com",
  "telefono": "+5491166662345"
}')"
check "POST /ingest (segundo)" 200 "$CODE" "$BODY"
echo ""

# --- 17. Verificar paginacion de leads --------------------------------------
echo "[17] Paginacion de leads (page_size=1)"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID/leads?page=1&page_size=1")"
check "GET leads paginado" 200 "$CODE" "$BODY"

LEADS_TOTAL=$(extract_json "$BODY" "total")
echo "    Total leads: $LEADS_TOTAL (esperado >= 2)"
echo ""

# --- 18. Lead no encontrado --------------------------------------------------
echo "[18] Lead no encontrado (404)"
parse_response "$(do_request GET "$BASE_URL/api/v1/admin/leads/00000000-0000-0000-0000-000000000000")"
check "GET /admin/leads/{id} inexistente" 404 "$CODE" "$BODY"
echo ""

# --- 19. Ingest con api_key invalida ----------------------------------------
echo "[19] Ingest con api_key invalida (404)"
parse_response "$(do_request POST "$BASE_URL/api/v1/ingest/clave_falsa_12345" '{"test": true}')"
check "POST /ingest con key invalida" 404 "$CODE" "$BODY"
echo ""

# --- 20. Eliminar campo -----------------------------------------------------
echo "[20] Eliminar campo"
parse_response "$(do_request DELETE "$BASE_URL/api/v1/admin/fields/$FIELD_ID")"
check "DELETE /admin/fields/{id}" 204 "$CODE" "$BODY"
echo ""

# --- 21. Soft-delete cuenta --------------------------------------------------
echo "[21] Soft-delete cuenta de prueba"
parse_response "$(do_request DELETE "$BASE_URL/api/v1/admin/accounts/$ACCOUNT_ID")"
check "DELETE /admin/accounts/{id}" 204 "$CODE" "$BODY"
echo ""

# --- 22. Ingest a cuenta desactivada ----------------------------------------
echo "[22] Ingest a cuenta desactivada (404)"
parse_response "$(do_request POST "$BASE_URL/api/v1/ingest/$API_KEY" '{"test": true}')"
check "POST /ingest cuenta inactiva" 404 "$CODE" "$BODY"
echo ""

# =============================================================================
echo "============================================"
echo " Resultados"
echo "============================================"
echo "  Pasaron:  $PASS"
echo "  Fallaron: $FAIL"
echo "  Total:    $((PASS + FAIL))"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
