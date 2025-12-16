# Локальная проверка работы решения

Дата проверки: 2025-12-16

## 1. Инфраструктура

Все контейнеры запущены и работают.

Команда: `docker compose ps`

Результат: Все 10 контейнеров в статусе "Up"

---

## 2. Исходные данные в базах данных

### CRM Database
Таблица: customers
Количество записей: 3

Команда:
```bash
docker compose exec crm_db psql -U crm_user -d crm_db -c "SELECT COUNT(*) FROM customers;"
```

Результат: 3

### Telemetry Database
Таблица: telemetry_data
Количество записей: 4500

Команда:
```bash
docker compose exec telemetry_db psql -U telemetry_user -d telemetry_db -c "SELECT COUNT(*) FROM telemetry_data;"
```

Результат: 4500

Скриншот: [screenshots/02_crm_telemetry_count.png](screenshots/02_crm_telemetry_count.png)

---

## 3. Выполнение ETL процесса в Airflow

DAG: reports_etl_dag

Все таски выполнены успешно:
- extract_crm - success
- extract_telemetry - success
- transform_and_load - success

Скриншот: [screenshots/03_airflow_dag_graph.png](screenshots/03_airflow_dag_graph.png)

---

## 4. Данные в ClickHouse

Таблица: reports_data_mart
База данных: reports_db
Количество записей: 3

Команды:
```bash
docker compose exec clickhouse clickhouse-client --query "SHOW TABLES FROM reports_db"
docker compose exec clickhouse clickhouse-client --query "SELECT COUNT(*) FROM reports_db.reports_data_mart"
docker compose exec clickhouse clickhouse-client --query "SELECT user_id, date, customer_name, total_movements FROM reports_db.reports_data_mart LIMIT 3"
```

Результат:
- Таблица reports_data_mart существует
- COUNT: 3
- Данные содержат корректные метрики

Скриншот: [screenshots/05_clickhouse_data.png](screenshots/05_clickhouse_data.png)

---

## 5. Backend API

### Health Check
URL: http://localhost:8000/health

Результат:
```json
{
  "status": "healthy",
  "service": "reports-api"
}
```

Статус: 200 OK

### Логи API

Команда:
```bash
docker compose logs reports-api --tail=30 --timestamps
```

Результат: Все запросы возвращают 200 OK:
- GET /health HTTP/1.1" 200 OK
- GET /reports?format=json HTTP/1.1" 200 OK
- GET /reports?format=csv HTTP/1.1" 200 OK

Скриншот: [screenshots/09_api_reports_logs.png](screenshots/09_api_reports_logs.png)

---

## 6. Frontend и отчёты

### Страница отчётов
URL: http://localhost:3000

Функциональность:
- Авторизация через Keycloak работает
- Отчёты загружаются и отображаются корректно
- Данные включают сводку и детальные данные

Скриншот: [screenshots/10_front_report_page.png](screenshots/10_front_report_page.png)

### Network DevTools - JSON запрос

Запрос: GET /reports?format=json

Результат:
- Статус: 200 OK
- Response содержит JSON с данными отчёта

### Network DevTools - CSV запрос

Запрос: GET /reports?format=csv

Результат:
- Статус: 200 OK
- Content-Type: text/csv; charset=utf-8
- Content-Disposition: attachment; filename=report_prothetic1_20251216.csv

Скриншот: [screenshots/12_front_network_csv.png](screenshots/12_front_network_csv.png)

---

## Примечание

Если при проверке таблицы telemetry_data и customers показывают COUNT = 0, это означает, что init скрипты не выполнились. PostgreSQL выполняет скрипты из /docker-entrypoint-initdb.d/ только при первом создании БД.

Решение:
```bash
docker compose down
rm -rf crm-data telemetry-data
docker compose up -d
```

Подождать 10-15 секунд для инициализации БД. После этого данные будут загружены автоматически.
