# Sprint 9 - BionicPRO

## Описание заданий

### Задание 1: Повышение безопасности системы

#### Задача 1: Диаграмма архитектуры управления идентификацией
Создана C4 диаграмма архитектурного решения для управления идентификацией пользователей. Решение обеспечивает унификацию доступа через внешние IdP (Россия, ЕС, Другие), безопасную схему работы с токенами без передачи IdP токенов фронтенду, поддержку различных внешних удостоверяющих служб в разных странах и локальное хранение персональных данных.

**Диаграмма:**
- [architecture-c4-identity-management.drawio](diagrams/architecture-c4-identity-management.drawio)
- [architecture-c4-identity-management.jpeg](diagrams/architecture-c4-identity-management.jpeg)

#### Задача 2: Реализация PKCE
Заменен Authorization Code Grant на PKCE (Proof Key for Code Exchange) для повышения безопасности. Реализовано в Keycloak и Frontend.

**Файлы:**
- `keycloak/realm-export.json` - конфигурация Keycloak с PKCE
- `frontend/src/utils/pkce.ts` - утилиты для генерации code_verifier и code_challenge
- `frontend/src/App.tsx` - инициализация Keycloak с PKCE

### Задание 2: Разработка сервиса отчётов

#### Задача 1: Диаграмма архитектуры сервиса отчётов
Создана C4 диаграмма архитектурного решения для генерации и получения отчётов. Решение включает ETL-процесс, объединяющий данные с датчиков и данные из CRM через Apache Airflow, формирование витрины отчётности в OLAP БД (ClickHouse) и бэкенд-сервис API для получения отчётов.

**Диаграмма:**
- [architecture-c4-reports-service.drawio](diagrams/architecture-c4-reports-service.drawio)
- [architecture-c4-reports-service.jpg](diagrams/architecture-c4-reports-service.jpg)

#### Задача 2: Airflow DAG для ETL процесса
Реализован DAG для запланированного выполнения ETL процесса, который извлекает данные из CRM и Telemetry баз данных и загружает их в витрину данных ClickHouse.

**Файлы:**
- `airflow/dags/reports_etl_dag.py` - DAG для ETL процесса

#### Задача 3: Backend API для получения отчётов
Создан FastAPI сервис с endpoint `/reports` для получения отчётов из ClickHouse в форматах JSON и CSV.

**Файлы:**
- `backend/main.py` - FastAPI приложение

#### Задача 4: Ограничения доступа
Реализована проверка JWT токена и фильтрация данных по user_id, обеспечивающая доступ пользователей только к своим отчётам.

#### Задача 5: UI для получения отчётов
Добавлены кнопки в интерфейсе для загрузки и скачивания отчётов.

**Файлы:**
- `frontend/src/components/ReportPage.tsx` - компонент для работы с отчётами

## Инструкция по проверке

### Запуск проекта

```bash
docker-compose up -d
```

**Ожидаемый результат:** Все контейнеры запущены и работают.

### Проверка Задания 1

#### Проверка PKCE в Keycloak
```bash
grep -A 10 'reports-frontend' keycloak/realm-export.json
```

**Ожидаемый результат:** В выводе должны быть:
- `"publicClient": true`
- `"implicitFlowEnabled": false`
- `"directAccessGrantsEnabled": false`
- `"pkce.code.challenge.method": "S256"`

#### Проверка PKCE в Frontend
```bash
cat frontend/src/utils/pkce.ts
cat frontend/src/App.tsx | grep -A 5 "pkceMethod"
```

**Ожидаемый результат:**
- В `pkce.ts` должны быть функции: `generateCodeVerifier()`, `generateCodeChallenge()`, `generatePKCEPair()`
- В `App.tsx` должна быть строка: `pkceMethod: 'S256'`

### Проверка Задания 2

#### Проверка Airflow DAG
```bash
docker-compose exec airflow-webserver airflow dags list | grep reports_etl_dag
```

**Ожидаемый результат:** В списке должен быть DAG `reports_etl_dag`.

#### Проверка Backend API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/reports
```

**Ожидаемый результат:**
- `curl http://localhost:8000/health` возвращает `{"status":"healthy","service":"reports-api"}`
- `curl http://localhost:8000/reports` возвращает `403 Forbidden` (без токена)

#### Проверка Frontend
Откройте http://localhost:3000

**Ожидаемый результат:** Открывается интерфейс с кнопкой "Войти" или страница с отчётами (если уже авторизован).

#### Проверка ограничений доступа
1. Войдите как пользователь `prothetic1` через http://localhost:3000
2. Нажмите "Загрузить отчёт" - должны быть видны только данные для `prothetic1`
3. Без авторизации попытка загрузить отчёт должна быть заблокирована

**Ожидаемый результат:**
- Неаутентифицированные пользователи не могут получить отчёт
- Аутентифицированные пользователи видят только свои данные
- Отчёты запрашиваются из OLAP базы (ClickHouse)

#### Проверка данных в ClickHouse
```bash
docker-compose exec clickhouse clickhouse-client
```

В консоли ClickHouse:
```sql
USE reports_db;
SELECT COUNT(*) FROM reports_data_mart;
SELECT * FROM reports_data_mart LIMIT 5;
```

**Ожидаемый результат:**
- `SELECT COUNT(*)` возвращает количество записей (больше 0 после выполнения ETL)
- `SELECT * LIMIT 5` возвращает данные из витрины данных

#### Проверка ETL процесса
```bash
docker-compose exec crm_db psql -U crm_user -d crm_db -c "SELECT COUNT(*) FROM customers;"
docker-compose exec telemetry_db psql -U telemetry_user -d telemetry_db -c "SELECT COUNT(*) FROM telemetry_data;"
docker-compose exec airflow-scheduler airflow dags trigger reports_etl_dag
```

**Ожидаемый результат:**
- Первые две команды возвращают количество записей в источниках данных (больше 0)
- Третья команда запускает DAG и возвращает сообщение об успешном запуске
- После выполнения ETL данные появляются в ClickHouse витрине

**Важно:** Отчёты генерируются только за периоды, которые уже обработаны Airflow. Если запросить данные за период, который еще не обработан, в отчёте будет пустой результат.

## Учетные данные для тестирования

Данные пользователей находятся в `keycloak/realm-export.json`. По умолчанию:
- Realm: `reports-realm`
- Client: `reports-frontend`
- Пользователи: `prothetic1`, `prothetic2`, `prothetic3` (пароли в realm-export.json)

## Порты сервисов

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Keycloak: http://localhost:8080
- Airflow: http://localhost:8081
- ClickHouse: http://localhost:8123
- CRM DB: localhost:5434
- Telemetry DB: localhost:5435

