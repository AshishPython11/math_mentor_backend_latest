import os
import re
import psycopg2
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from src.configs.settings import settings
from src.configs.config import DATABASE_URL
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends , Request, status
import random
from fastapi.security import OAuth2PasswordBearer
from src.common.app_response import AppResponse
from src.common.app_constants import AppConstants
from src.common.messages import Messages
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

token_auth_scheme = HTTPBearer()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app_response = AppResponse()

def table_exists(cursor, table_name):
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);", (table_name,))
    return cursor.fetchone()[0]

def extract_version(filename):
    # Use regex to find the numeric part of the filename
    match = re.search(r'V(\d+)', filename)
    return int(match.group(1)) if match else float('inf')  # Return a large number if no match




def execute_sql_files():
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Ensure the migrations table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL UNIQUE,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()

    # Get the list of already executed files
    cursor.execute("SELECT file_name FROM migrations;")
    executed_files = {row[0] for row in cursor.fetchall()}

    # Get absolute path for the database directory
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DATABASE_DIR = os.path.join(BASE_DIR, "database")  # Correct path

    # Ensure the directory exists
    if not os.path.exists(DATABASE_DIR):
        raise FileNotFoundError(f"Database directory not found: {DATABASE_DIR}")

    sql_files = sorted(os.listdir(DATABASE_DIR), key=extract_version)
    
    for file_name in sql_files:
        if file_name not in executed_files:
            file_path = os.path.join(DATABASE_DIR, file_name)  # Correct path

            # Ensure the file exists
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"SQL file not found: {file_path}")

            with open(file_path, "r") as file:
                sql = file.read()

                # Extract table name (assuming one table per file)
                first_line = sql.strip().split("\n")[0].strip().lower()
                if first_line.startswith("create table"):
                    table_name = first_line.split(" ")[2]
                    table_name = table_name.replace("if not exists", "").strip("();")

                    # Check if the table already exists
                    if table_exists(cursor, table_name):
                        print(f"Skipping {file_name}: Table {table_name} already exists.")
                        continue

                # Execute the SQL script
                print(f"Executing: {file_name}")
                cursor.execute(sql)
                cursor.execute("INSERT INTO migrations (file_name) VALUES (%s);", (file_name,))
                conn.commit()
                print(f"Executed: {file_name}")

    cursor.close()
    conn.close()


def hash_password(password: str) -> str:
    """ Hashes a plain  password. """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Verifies a plain password against its hashed version. """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta):
    """ Creates a JWT access token with expiration. """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError: 
            raise HTTPException(
            status_code=401,
            detail=Messages.INVALID_TOKEN, 
            headers={"WWW-Authenticate": "Bearer"},
        )
    


async def send_email(recipient: str, subject: str, body: str):
    try:
        message = MIMEMultipart()
        message["From"] = settings.GMAIL_USERNAME
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))
        

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.GMAIL_USERNAME,   
            password=settings.GMAIL_PASSWORD,
        )
        return True
    except Exception as e:
        return False


def generate_otp():
    return str(random.randint(100000, 999999))  # Generate a 6-digit OTP



def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme)):
    print("get_current_user")
    """Extract and verify JWT token"""
    token = credentials.credentials  # ✅ Extract the actual token string

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                # Check if payload contains user info
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=403,
                detail="Token does not contain user info"
            )
        return payload  # ✅ Return decoded user info
    
    except JWTError as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )