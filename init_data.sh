#!/bin/bash
# Скрипт для проверки и инициализации данных в БД

set -e

echo "Проверка данных в CRM и Telemetry базах..."

CRM_COUNT=$(docker compose exec -T crm_db psql -U crm_user -d crm_db -t -c "SELECT COUNT(*) FROM customers;" 2>/dev/null | tr -d ' ' || echo "0")
TELEMETRY_COUNT=$(docker compose exec -T telemetry_db psql -U telemetry_user -d telemetry_db -t -c "SELECT COUNT(*) FROM telemetry_data;" 2>/dev/null | tr -d ' ' || echo "0")

echo "CRM customers: $CRM_COUNT"
echo "Telemetry data: $TELEMETRY_COUNT"

if [ "$CRM_COUNT" -eq "0" ] || [ "$TELEMETRY_COUNT" -eq "0" ]; then
    echo ""
    echo "ВНИМАНИЕ: Одна или обе таблицы пустые!"
    echo "PostgreSQL выполняет init скрипты только при первом создании БД."
    echo ""
    echo "Для инициализации данных выполните:"
    echo "  1. docker compose down"
    echo "  2. rm -rf crm-data telemetry-data"
    echo "  3. docker compose up -d"
    echo "  4. Подождите 10-15 секунд для инициализации"
    echo ""
    exit 1
else
    echo ""
    echo "Данные присутствуют. Можно запускать ETL процесс."
    exit 0
fi

