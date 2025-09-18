import re
from bs4 import BeautifulSoup

def clean_html_content(html_content: str) -> str:
    """
    Pulisce il contenuto HTML dei ticket e lo converte in testo leggibile
    Da integrare nella funzione get_ticket_by_id del Ticket Server
    """
    if not html_content or html_content.strip() == "":
        return ""
    
    try:
        # Parse HTML con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Converti liste HTML in testo naturale
        for ul in soup.find_all(['ul', 'ol']):
            items = []
            for li in ul.find_all('li'):
                item_text = li.get_text(strip=True)
                if item_text:
                    items.append(f"• {item_text}")
            
            if items:
                # Sostituisci la lista con testo formattato
                list_text = "\n" + "\n".join(items) + "\n"
                ul.replace_with(list_text)
        
        # Converti tabelle in testo leggibile
        for table in soup.find_all('table'):
            table_text = []
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
                    if len(cell_texts) >= 2:
                        table_text.append(f"{cell_texts[0]}: {' | '.join(cell_texts[1:])}")
            
            if table_text:
                formatted_table = "\n" + "\n".join(table_text) + "\n"
                table.replace_with(formatted_table)
        
        # Gestisci i div di quote/citazioni
        for blockquote in soup.find_all(['blockquote', 'div']):
            if blockquote.get('class') and 'quote' in str(blockquote.get('class')):
                quote_text = blockquote.get_text(strip=True)
                if quote_text:
                    blockquote.replace_with(f"\n> {quote_text}\n")
        
        # Converti paragrafi in testo con spazi
        for p in soup.find_all('p'):
            p.replace_with(p.get_text() + "\n\n")
        
        # Converti br in newline
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # Estrai tutto il testo rimanente
        text = soup.get_text()
        
        # Pulizia del testo finale
        # Rimuovi spazi multipli ma mantieni i newline
        text = re.sub(r'[ \t]+', ' ', text)  # Spazi e tab multipli → singolo spazio
        text = re.sub(r'\n{3,}', '\n\n', text)  # Più di 2 newline → 2 newline
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Spazi a inizio/fine riga
        
        # Pulizia caratteri speciali comuni nell'HTML
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        
        # Rimuovi sequenze di caratteri strani da email HTML
        text = re.sub(r'<o:p[^>]*>', '', text)
        text = re.sub(r'</o:p>', '', text)
        text = re.sub(r'mso-[^;]+;?', '', text)
        
        return text.strip()
        
    except Exception as e:
        # In caso di errore nel parsing HTML, restituisci il testo grezzo pulito
        print(f"Errore nella pulizia HTML: {e}")
        # Fallback: rimuovi solo i tag HTML base
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()


def format_ticket_data(ticket_data: list) -> list:
    """
    Formatta i dati del ticket applicando la pulizia HTML
    Da chiamare prima di restituire i dati in get_ticket_by_id
    """
    formatted_data = []
    
    for entry in ticket_data:
        # Crea una copia dell'entry
        formatted_entry = entry.copy()
        
        # Pulisci il contenuto HTML se presente
        if 'dt_testo' in formatted_entry and formatted_entry['dt_testo']:
            formatted_entry['dt_testo'] = clean_html_content(formatted_entry['dt_testo'])
        
        formatted_data.append(formatted_entry)
    
    return formatted_data