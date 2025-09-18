"""
Modulo per gestione database ChromaDB e PostgreSQL
"""

import os
import logging
import chromadb
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Configurazione ChromaDB - usa path assoluto rispetto al file corrente
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "ticket_DB")
COLLECTION_NAME = "tickets_support"

# Configurazione PostgreSQL per ticket
POSTGRES_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def get_postgres_connection():
    """
    Ottieni connessione al database PostgreSQL per i ticket
    
    Returns: psycopg2.connection: Connessione al database
        
    Raises: Exception: Se non riesce a connettersi
    """
    try:
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG['port'],
            database=POSTGRES_CONFIG['database'],
            user=POSTGRES_CONFIG['user'],
            password=POSTGRES_CONFIG['password'],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Errore connessione PostgreSQL: {e}")
        raise

def get_collection():
    """
    Ottieni la collezione ChromaDB per i ticket
    
    Returns: Collection: La collezione ChromaDB
        
    Raises: Exception: Se non riesce a connettersi
    """
    try:
        os.makedirs(DB_PATH, exist_ok=True)
        
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection
        
    except Exception as e:
        logger.error(f"Errore nel recuperare la collezione: {e}")
        raise