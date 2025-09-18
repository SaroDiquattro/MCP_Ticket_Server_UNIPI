#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per pulire i ticket HTML e prepararli per Chroma DB
"""

import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata
from typing import Dict, List, Any

def clean_html_content(html_content: str) -> str:
    """Pulisce il contenuto HTML e lo converte in testo naturale"""
    if not html_content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Converti liste in testo naturale
    for ul in soup.find_all(['ul', 'ol']):
        items = []
        for li in ul.find_all('li'):
            item_text = li.get_text(strip=True)
            if item_text:
                items.append(item_text)
        
        if items:
            # Sostituisci la lista con testo naturale
            list_text = "I punti sono: " + ", ".join(items) + "."
            ul.replace_with(list_text)
    
    # Converti tabelle in testo leggibile
    for table in soup.find_all('table'):
        table_text = []
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
                if cell_texts:
                    table_text.append(": ".join(cell_texts))
        
        if table_text:
            formatted_table = ". ".join(table_text) + "."
            table.replace_with(formatted_table)
    
    # Estrai tutto il testo
    text = soup.get_text()
    
    # Pulizia generale
    text = re.sub(r'\s+', ' ', text)  # Spazi multipli → singolo
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Newline multipli → doppio
    text = text.strip()
    
    return text

def preprocess_text(text: str) -> str:
    """Applica tutti i preprocessi al testo"""
    if not text:
        return ""
    
    # Sostituisci URL con placeholder
    text = re.sub(r'https?://[^\s]+', '[URL]', text)
    
    # Sostituisci email con placeholder  
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Normalizza numeri di telefono
    text = re.sub(r'(\+39\s*)?(\d{3})\s*(\d{3})\s*(\d{4})', r'+39 \2 \3 \4', text)
    
    # Standardizza date (formato italiano)
    text = re.sub(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', r'\1/\2/\3', text)
    
    # Rimuovi spazi eccessivi
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def process_tickets(input_file: str, output_file: str):
    """Processa i ticket dal file di input e crea il file ottimizzato per Chroma"""
    
    print(f"Caricamento file {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            tickets_data = json.load(f)
    except FileNotFoundError:
        print(f"Errore: File {input_file} non trovato!")
        return
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
        return
    
    # Estrai l'array di ticket dalla struttura SQL
    if isinstance(tickets_data, dict):
        # Trova la chiave che contiene la query SQL (dovrebbe essere l'unica)
        sql_keys = list(tickets_data.keys())
        if len(sql_keys) == 1 and isinstance(tickets_data[sql_keys[0]], list):
            tickets = tickets_data[sql_keys[0]]
            print(f"Query SQL rilevata: {sql_keys[0][:100]}...")
        else:
            print("Formato file non riconosciuto! Atteso: {'query_sql': [array_ticket]}")
            return
    elif isinstance(tickets_data, list):
        # Fallback per array diretto
        tickets = tickets_data
    else:
        print("Formato file non riconosciuto!")
        return
    
    print(f"Elaborazione di {len(tickets)} ticket...")
    
    processed_documents = []
    
    for i, ticket in enumerate(tickets):
        try:
            # Estrai i campi necessari
            ttnumtic = ticket.get('ttnumtic', '')
            title = ticket.get('ttshotxt', '')
            company = ticket.get('cotitle', '')
            html_content = ticket.get('dt_testo', '')
            date_str = ticket.get('dt__data', '')
            
            # Pulisci il contenuto HTML
            clean_text = clean_html_content(html_content)
            
            # Applica preprocessi
            processed_text = preprocess_text(clean_text)
            
            # Estrai l'anno dalla data
            year = "2024"  # Default
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    year = str(date_obj.year)
                except:
                    pass
            
            # Crea ID nel formato richiesto
            ticket_id = f"{ttnumtic}/SPC-{year}"
            
            # Crea il documento per Chroma
            document = {
                "id": ticket_id,
                "text": processed_text,
                "metadata": {
                    "title": title,
                    "company": company,
                    "date": date_str.split('T')[0] if 'T' in date_str else date_str,
                    "year": year,
                    "original_id": ttnumtic,
                }
            }
            
            processed_documents.append(document)
            
            # Progress update ogni 100 ticket
            if (i + 1) % 100 == 0:
                print(f"Processati {i + 1}/{len(tickets)} ticket...")
                
        except Exception as e:
            print(f"Errore nel processare ticket {i}: {e}")
            continue
    
    # Crea la struttura finale per Chroma
    chroma_data = {
        "documents": processed_documents,
        "metadata": {
            "total_documents": len(processed_documents),
            "processing_date": datetime.now().isoformat(),
            "source_file": input_file
        }
    }
    
    # Salva il file ottimizzato
    print(f"Salvataggio in {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chroma_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Elaborazione completata!")
        print(f"📊 Statistiche:")
        print(f"   - Ticket processati: {len(processed_documents)}")
        print(f"   - File salvato: {output_file}")
            
    except Exception as e:
        print(f"Errore nel salvare il file: {e}")

def main():
    """Funzione principale"""
    input_file = "ticket_totali_sporchi.json"
    output_file = "ticket_totali_chroma.json"
    
    print("🎫 Script di pulizia ticket per Chroma DB")
    print("=" * 50)
    
    process_tickets(input_file, output_file)

if __name__ == "__main__":
    main()