"""
Airflow DAG for Reports ETL Process
Extracts data from CRM and Telemetry databases,
transforms and loads into ClickHouse Data Mart
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import psycopg2
from clickhouse_driver import Client
import json

# Default arguments
default_args = {
    'owner': 'bionicpro',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'reports_etl_dag',
    default_args=default_args,
    description='ETL process for Reports Data Mart',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['reports', 'etl', 'clickhouse'],
)

# Connection parameters
CRM_DB_CONFIG = {
    'host': 'crm_db',
    'port': 5432,
    'database': 'crm_db',
    'user': 'crm_user',
    'password': 'crm_password'
}

TELEMETRY_DB_CONFIG = {
    'host': 'telemetry_db',
    'port': 5432,
    'database': 'telemetry_db',
    'user': 'telemetry_user',
    'password': 'telemetry_password'
}

CLICKHOUSE_CONFIG = {
    'host': 'clickhouse',
    'port': 9000,
    'database': 'reports_db',
    'user': 'default',
    'password': ''
}


def extract_crm_data(**context):
    """Extract customer and prosthesis data from CRM database"""
    try:
        print(f"Connecting to CRM database at {CRM_DB_CONFIG['host']}:{CRM_DB_CONFIG['port']}")
        conn = psycopg2.connect(**CRM_DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            c.user_id,
            c.email as customer_email,
            c.first_name || ' ' || c.last_name as customer_name,
            p.prothesis_id,
            p.model,
            p.manufactured_date,
            p.warranty_until
        FROM customers c
        LEFT JOIN protheses p ON c.id = p.customer_id
        WHERE p.prothesis_id IS NOT NULL
        """
        
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        context['ti'].xcom_push(key='crm_data', value=results)
        print(f"SUCCESS: Extracted {len(results)} records from CRM")
        if results:
            print(f"Sample CRM record: {results[0]}")
        return results
    except Exception as e:
        print(f"ERROR: Failed to extract CRM data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def extract_telemetry_data(**context):
    """Extract and aggregate telemetry data from Telemetry database"""
    try:
        print(f"Connecting to Telemetry database at {TELEMETRY_DB_CONFIG['host']}:{TELEMETRY_DB_CONFIG['port']}")
        conn = psycopg2.connect(**TELEMETRY_DB_CONFIG)
        cursor = conn.cursor()
        
        execution_date = context['execution_date']
        start_date = execution_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        print(f"Extracting telemetry data from {start_date} to {end_date}")
        
        query = """
        SELECT 
            user_id,
            prothesis_id,
            DATE(timestamp) as date,
            COUNT(*) as total_movements,
            AVG(response_time_ms) as avg_response_time_ms,
            AVG(battery_level_percent) as battery_usage_percent,
            MAX(battery_cycle_count) as battery_cycles,
            COUNT(CASE WHEN error_code IS NOT NULL THEN 1 END) as error_count,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 3600 as usage_hours,
            MAX(timestamp) as last_activity
        FROM telemetry_data
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY user_id, prothesis_id, DATE(timestamp)
        """
        
        cursor.execute(query, (start_date, end_date))
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        context['ti'].xcom_push(key='telemetry_data', value=results)
        print(f"SUCCESS: Extracted {len(results)} records from Telemetry")
        if results:
            print(f"Sample telemetry record: {results[0]}")
        return results
    except Exception as e:
        print(f"ERROR: Failed to extract telemetry data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def transform_and_load(**context):
    """Transform and load data into ClickHouse Data Mart"""
    try:
        crm_data = context['ti'].xcom_pull(key='crm_data', task_ids='extract_crm')
        telemetry_data = context['ti'].xcom_pull(key='telemetry_data', task_ids='extract_telemetry')
        
        if not crm_data:
            print("WARNING: No CRM data extracted")
            crm_data = []
        
        if not telemetry_data:
            print("WARNING: No telemetry data extracted")
            telemetry_data = []
        
        crm_lookup = {}
        for record in crm_data:
            key = (record['user_id'], record['prothesis_id'])
            crm_lookup[key] = record
        
        # Connect to ClickHouse
        print(f"Connecting to ClickHouse at {CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}")
        client = Client(**CLICKHOUSE_CONFIG)
        
        # Test connection and create database/table if needed
        try:
            test_result = client.execute("SELECT 1")
            print(f"ClickHouse connection successful: {test_result}")
            
            # Create database if not exists
            client.execute(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_CONFIG['database']}")
            client.execute(f"USE {CLICKHOUSE_CONFIG['database']}")
            
            # Create table if not exists (ClickHouse doesn't auto-run init scripts)
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS reports_data_mart
            (
                user_id String,
                date Date,
                customer_name String,
                customer_email String,
                prothesis_id String,
                total_movements UInt64,
                avg_response_time_ms Float32,
                battery_usage_percent Float32,
                battery_cycles UInt32,
                error_count UInt32,
                usage_hours Float32,
                last_activity DateTime,
                movements_by_type Map(String, UInt64),
                daily_usage_hours Map(Date, Float32),
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (user_id, date, prothesis_id)
            SETTINGS index_granularity = 8192
            """
            
            client.execute(create_table_sql)
            print(f"Table reports_data_mart ensured in database {CLICKHOUSE_CONFIG['database']}")
                
        except Exception as e:
            print(f"ERROR: Failed to connect to ClickHouse or create table: {str(e)}")
            import traceback
            traceback.print_exc()
            client.disconnect()
            raise
        
        execution_date = context['execution_date']
        process_date = execution_date.date() if execution_date else datetime.now().date()
        
        insert_data = []
        for tel_record in telemetry_data:
            key = (tel_record['user_id'], tel_record['prothesis_id'])
            crm_record = crm_lookup.get(key, {})
            
            # Format Map fields for ClickHouse
            # For Map(String, UInt64) - empty map
            movements_by_type = {}  # Empty map as dict
            
            # For Map(Date, Float32) - need to use Date objects as keys
            # ClickHouse Map(Date, Float32) requires Date type as key
            daily_usage_hours = {process_date: float(tel_record.get('usage_hours', 0.0))}
            
            record = {
                'user_id': str(tel_record['user_id']),
                'date': tel_record['date'] or process_date,
                'customer_name': str(crm_record.get('customer_name', '')),
                'customer_email': str(crm_record.get('customer_email', '')),
                'prothesis_id': str(tel_record['prothesis_id']),
                'total_movements': int(tel_record.get('total_movements', 0)),
                'avg_response_time_ms': float(tel_record.get('avg_response_time_ms', 0.0)),
                'battery_usage_percent': float(tel_record.get('battery_usage_percent', 0.0)),
                'battery_cycles': int(tel_record.get('battery_cycles', 0)),
                'error_count': int(tel_record.get('error_count', 0)),
                'usage_hours': float(tel_record.get('usage_hours', 0.0)),
                'last_activity': tel_record.get('last_activity', datetime.now()),
                'movements_by_type': movements_by_type,
                'daily_usage_hours': daily_usage_hours,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            insert_data.append(record)
        
        if not insert_data:
            print("WARNING: No data to insert into ClickHouse")
            client.disconnect()
            return 0
        
        print(f"Preparing to insert {len(insert_data)} records into ClickHouse")
        columns = list(insert_data[0].keys())
        values = [[record[col] for col in columns] for record in insert_data]
        
        try:
            # Insert data
            client.execute(
                f"INSERT INTO reports_data_mart ({', '.join(columns)}) VALUES",
                values
            )
            print(f"SUCCESS: Loaded {len(insert_data)} records into ClickHouse Data Mart")
            
            # Verify insertion
            verify_query = f"SELECT COUNT(*) FROM reports_data_mart WHERE date = '{process_date}'"
            count_result = client.execute(verify_query)
            print(f"Verification: Found {count_result[0][0] if count_result else 0} records for date {process_date}")
            
        except Exception as e:
            print(f"ERROR: Failed to insert data into ClickHouse: {str(e)}")
            print(f"ERROR: Data sample (first record): {insert_data[0] if insert_data else 'No data'}")
            raise
        
        client.disconnect()
        return len(insert_data)
        
    except Exception as e:
        print(f"FATAL ERROR in transform_and_load: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# Define tasks
extract_crm_task = PythonOperator(
    task_id='extract_crm',
    python_callable=extract_crm_data,
    dag=dag,
)

extract_telemetry_task = PythonOperator(
    task_id='extract_telemetry',
    python_callable=extract_telemetry_data,
    dag=dag,
)

transform_load_task = PythonOperator(
    task_id='transform_and_load',
    python_callable=transform_and_load,
    dag=dag,
)

# Define task dependencies
[extract_crm_task, extract_telemetry_task] >> transform_load_task

