"""
MCP Tool per gestione diretta dei ticket dal gestionale PostgreSQL
"""

import json
import logging
import re
from decimal import Decimal
from psycopg2.extras import RealDictCursor

from .ticket_cleaner import format_ticket_data
from database import get_postgres_connection

logger = logging.getLogger(__name__)

def convert_decimals(obj):
    """Converte ricorsivamente tutti i Decimal in float per la serializzazione JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj

async def get_ticket_by_id(ticket_id: str) -> str:
    """
    Recupera un ticket specifico direttamente dal database PostgreSQL del gestionale
    
    Args:
        ticket_id: ID del ticket (es. "3906", "3906/SPC-2024", "3906/2024")
        
    Returns:
        str: JSON con i dettagli completi del ticket
    """
    def _sync_get_ticket(ticket_id: str) -> str:
        """Funzione interna sincrona per la query al database"""
    try:
        # Validazione input
        if not ticket_id or not ticket_id.strip():
            raise ValueError("L'ID del ticket non può essere vuoto")
        
        # Parsing del ticket_id per estrarre numero e anno
        ticket_number, year = parse_ticket_id(ticket_id.strip())
        
        # Connessione al database PostgreSQL
        conn = get_postgres_connection()
        
        try:
            # Query per recuperare il ticket completo
            query = """
            SELECT
                pv_tickets_m.TTNUMTIC,
                pv_tickets_m.TTSHOTXT,
                ba_contact.COTITLE,
                pv_tickets_d.DT_TESTO,
                pv_tickets_d.DT__DATA
            FROM (((pv_tickets_d001 pv_tickets_d
            LEFT OUTER JOIN pv_tickets_m001 pv_tickets_m ON pv_tickets_m.TTCODICE = pv_tickets_d.DTCODTIC)
            LEFT OUTER JOIN ba_contact ON pv_tickets_m.TTCODCOM = ba_contact.COCOMPANYID)
            LEFT OUTER JOIN pv_stati001 pv_stati ON pv_stati.STCODICE = pv_tickets_d.DT_STATO)
            WHERE (
                pv_tickets_m.TTNUMTIC = %s
                AND pv_tickets_m.TTCODCEN = '001'
                AND pv_tickets_d.DT__DATA >= %s
                AND pv_tickets_d.DT__DATA < %s
            )
            ORDER BY pv_tickets_d.DT__DATA DESC
            """
            
            # Parametri per la query
            start_date = f"{year}-01-01"
            end_date = f"{year + 1}-01-01"
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (ticket_number, start_date, end_date))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return json.dumps({
                    "status": "error",
                    "ticket_id": ticket_id,
                    "parsed_number": ticket_number,
                    "parsed_year": year,
                    "error": f"Ticket {ticket_number} non trovato per l'anno {year}",
                    "error_code": "TICKET_NOT_FOUND"
                }, ensure_ascii=False, indent=2)
            
            # Converte i record in lista di dict, gestendo i Decimal
            ticket_entries = []
            for row in rows:
                entry = dict(row)
                
                # Formatta la data se necessario
                if entry.get('dt__data'):
                    entry['dt__data'] = entry['dt__data'].isoformat()
                
                # Converte i Decimal per la serializzazione JSON
                entry = convert_decimals(entry)
                ticket_entries.append(entry)

                ticket_entries = format_ticket_data(ticket_entries)
            
            # Struttura la risposta
            response = {
                "status": "success",
                "ticket_id": ticket_id,
                "parsed_number": ticket_number,
                "parsed_year": year,
                "entries_count": len(ticket_entries),
                "ticket_data": ticket_entries
            }
            
            # Converte eventuali Decimal rimasti nella risposta
            response = convert_decimals(response)
            
            return json.dumps(response, ensure_ascii=False, indent=2)
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"❌ Errore nel recuperare ticket {ticket_id}: {e}")
        
        error_response = {
            "status": "error",
            "ticket_id": ticket_id,
            "error": str(e),
            "error_type": type(e).__name__
        }
        
        return json.dumps(error_response, ensure_ascii=False, indent=2)


def parse_ticket_id(ticket_id: str) -> tuple[str, int]:
    """
    Parsing del ticket ID per estrarre numero e anno
    
    Formati supportati:
    - "3906" -> numero: "3906", anno: anno corrente
    - "3906/SPC-2024" -> numero: "3906", anno: 2024
    - "3906/2024" -> numero: "3906", anno: 2024
    - "3906-2024" -> numero: "3906", anno: 2024
    
    Args:
        ticket_id: ID del ticket da parsare
        
    Returns:
        tuple: (numero_ticket, anno)
    """
    from datetime import datetime
    
    # Rimuovi spazi
    ticket_id = ticket_id.strip()
    
    # Pattern per estrarre numero e anno
    # Cerca pattern tipo: numero/qualcosa-anno o numero/anno o numero-anno
    patterns = [
        r'^(\d+)/[A-Za-z]*-?(\d{4})$',  # 3906/SPC-2024 o 3906/SPC2024
        r'^(\d+)/(\d{4})$',             # 3906/2024
        r'^(\d+)-(\d{4})$',             # 3906-2024
        r'^(\d+)$'                      # 3906 (solo numero)
    ]
    
    for pattern in patterns:
        match = re.match(pattern, ticket_id)
        if match:
            if len(match.groups()) == 2:
                # Numero e anno trovati
                number = match.group(1)
                year = int(match.group(2))
                return number, year
            elif len(match.groups()) == 1:
                # Solo numero, usa anno corrente
                number = match.group(1)
                current_year = datetime.now().year
                return number, current_year
    
    # Se nessun pattern corrisponde, prova a estrarre almeno il numero
    number_match = re.search(r'(\d+)', ticket_id)
    if number_match:
        number = number_match.group(1)
        current_year = datetime.now().year
        return number, current_year
    
    # Se non riesce a parsare nulla, solleva un'eccezione
    raise ValueError(f"Formato ticket ID non riconosciuto: {ticket_id}")