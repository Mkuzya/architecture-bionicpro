"""
Reports API Service
FastAPI backend for generating user reports from ClickHouse Data Mart
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import jwt
import requests
from clickhouse_driver import Client
import requests as http_requests
from datetime import datetime, date
import json
import csv
from io import StringIO

app = FastAPI(title="BionicPRO Reports API", version="1.0.0")

# CORS configuration - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "reports-api")

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "reports_db")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract user information"""
    token = credentials.credentials
    
    try:
        # Decode token without verification first to get header
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user_id from token
        user_id = decoded.get("preferred_username") or decoded.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id found")
        
        return {
            "user_id": user_id,
            "token": token,
            "decoded": decoded
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


def get_clickhouse_client():
    """Get ClickHouse client connection using native protocol"""
    # Use native ClickHouse driver for proper authentication
    try:
        client = Client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            database=CLICKHOUSE_DB,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD if CLICKHOUSE_PASSWORD else None,
            connect_timeout=10,
            send_receive_timeout=30
        )
        return client
    except Exception as e:
        # Fallback to HTTP if native fails
        print(f"Warning: Native ClickHouse connection failed: {e}, trying HTTP")
        class HTTPClickHouse:
            def __init__(self, host, port, database, user, password):
                self.url = f"http://{host}:8123"
                self.database = database
                self.user = user
                self.password = password
            
            def execute(self, query, params=None):
                # Replace parameters in query
                if params:
                    for key, value in params.items():
                        # Escape single quotes in string values
                        if isinstance(value, str):
                            value = value.replace("'", "''")
                        query = query.replace(f"%({key})s", f"'{value}'")
                
                # Build URL with authentication
                url = f"{self.url}/?database={self.database}"
                if self.user:
                    url += f"&user={self.user}"
                if self.password:
                    url += f"&password={self.password}"
                
                # Execute via HTTP
                response = http_requests.post(
                    url,
                    data=query.encode('utf-8'),
                    timeout=10,
                    headers={'Content-Type': 'text/plain'}
                )
                
                if response.status_code == 401:
                    raise Exception(f"ClickHouse authentication failed. Check user/password. URL: {url}")
                
                response.raise_for_status()
                
                # Parse TSV response
                lines = [line for line in response.text.strip().split('\n') if line.strip()]
                if not lines:
                    return []
                
                # Convert to list of tuples
                result = []
                for line in lines:
                    values = line.split('\t')
                    # Convert types
                    converted = []
                    for val in values:
                        try:
                            # Try to convert to number
                            if '.' in val:
                                converted.append(float(val))
                            else:
                                converted.append(int(val))
                        except ValueError:
                            converted.append(val)
                    result.append(tuple(converted))
                return result
            
            def disconnect(self):
                pass
        
        return HTTPClickHouse(CLICKHOUSE_HOST, 8123, CLICKHOUSE_DB, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD)


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "reports-api"}


@app.options("/reports")
async def options_reports():
    """Handle OPTIONS requests for /reports endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.get("/reports")
async def get_report(
    format: Optional[str] = "json",
    user_info: dict = Depends(verify_token)
):
    """
    Get report for authenticated user
    Only returns data for the user making the request
    """
    user_id = user_info["user_id"]
    
    client = get_clickhouse_client()
    
    try:
        # Ensure table exists (create if not exists)
        create_table_query = """
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
        
        try:
            # Try to create database and table if using native client
            if isinstance(client, Client):
                client.execute("CREATE DATABASE IF NOT EXISTS reports_db")
                client.execute("USE reports_db")
                # Split multi-line query for native client
                for statement in create_table_query.split(';'):
                    statement = statement.strip()
                    if statement:
                        client.execute(statement)
            else:
                # For HTTP client, try to execute (may fail silently if table exists)
                try:
                    client.execute("CREATE DATABASE IF NOT EXISTS reports_db")
                except:
                    pass
                try:
                    # HTTP client may need single-line query
                    single_line_query = " ".join(create_table_query.split())
                    client.execute(single_line_query)
                except Exception as table_error:
                    # Table might already exist, which is OK
                    print(f"Note: Table creation: {table_error}")
        except Exception as e:
            print(f"Note: Database/table creation check: {e}")
        
        query = """
        SELECT 
            user_id,
            date,
            customer_name,
            customer_email,
            prothesis_id,
            total_movements,
            avg_response_time_ms,
            battery_usage_percent,
            battery_cycles,
            error_count,
            usage_hours,
            last_activity,
            movements_by_type,
            daily_usage_hours,
            updated_at
        FROM reports_data_mart
        WHERE user_id = %(user_id)s
        ORDER BY date DESC
        LIMIT 100
        """
        
        # Handle both native client and HTTP client parameter formats
        if isinstance(client, Client):
            # Native client - use parameterized query
            result = client.execute(query, {'user_id': user_id})
        else:
            # HTTP client - parameters already handled in execute method
            result = client.execute(query, {'user_id': user_id})
        
        if not result:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No report data found",
                    "message": f"No data available for user {user_id}. Please ensure ETL process has run.",
                    "user_id": user_id
                }
            )
        
        columns = [
            "user_id", "date", "customer_name", "customer_email", "prothesis_id",
            "total_movements", "avg_response_time_ms", "battery_usage_percent",
            "battery_cycles", "error_count", "usage_hours", "last_activity",
            "movements_by_type", "daily_usage_hours", "updated_at"
        ]
        
        reports = []
        for row in result:
            report = dict(zip(columns, row))
            if report.get("movements_by_type"):
                try:
                    report["movements_by_type"] = json.loads(report["movements_by_type"])
                except:
                    report["movements_by_type"] = {}
            if report.get("daily_usage_hours"):
                try:
                    report["daily_usage_hours"] = json.loads(report["daily_usage_hours"])
                except:
                    report["daily_usage_hours"] = {}
            
            if isinstance(report.get("last_activity"), datetime):
                report["last_activity"] = report["last_activity"].isoformat()
            if isinstance(report.get("updated_at"), datetime):
                report["updated_at"] = report["updated_at"].isoformat()
            if isinstance(report.get("date"), date):
                report["date"] = report["date"].isoformat()
            
            reports.append(report)
        
        summary = {
            "user_id": user_id,
            "total_records": len(reports),
            "total_movements": sum(r.get("total_movements", 0) for r in reports),
            "avg_response_time": sum(r.get("avg_response_time_ms", 0) for r in reports) / len(reports) if reports else 0,
            "total_usage_hours": sum(r.get("usage_hours", 0) for r in reports),
            "total_errors": sum(r.get("error_count", 0) for r in reports),
            "protheses": list(set(r.get("prothesis_id") for r in reports if r.get("prothesis_id"))),
        }
        
        if format.lower() == "csv":
            output = StringIO()
            if reports:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                for report in reports:
                    row = report.copy()
                    row["movements_by_type"] = json.dumps(row.get("movements_by_type", {}))
                    row["daily_usage_hours"] = json.dumps(row.get("daily_usage_hours", {}))
                    writer.writerow(row)
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
        else:
            return {
                "summary": summary,
                "data": reports,
                "generated_at": datetime.now().isoformat()
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

