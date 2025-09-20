"""
Tool per ricerca semantica sui ticket
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from database import get_collection

logger = logging.getLogger(__name__)

async def search_similar_tickets(query_text: str, n_results: int = 5) -> str:
    """
    Cerca ticket simili tramite ricerca semantica utilizzando embedding vettoriali.
    La funzione converte il testo di ricerca in un vettore e trova i ticket
    più simili nel database basandosi sulla distanza coseno tra i vettori.
    
    Args:
        - query_text: Testo da cercare
        - n_results: Numero di risultati da restituire
        
    Returns: str: JSON con i risultati della ricerca
    """
    try:
        # Validazione input
        # Controlla che la query non sia vuota o contenga solo spazi
        if not query_text or not query_text.strip():
            raise ValueError("Il testo di ricerca non può essere vuoto")
        
        # Limita i risultati tra 1 e 20
        if n_results < 1 or n_results > 20: 
            raise ValueError("Il numero di risultati deve essere tra 1 e 20")
        
        # Ottieni la collezione ChromaDB contenente i ticket indicizzati
        collection = get_collection()
        
        results = collection.query( 
            query_texts=[query_text.strip()], # lista di testi da cercare senza spazi
            n_results=n_results 
        )
        
        # Formatta i risultati
        formatted_results = []
        
        if not results['ids'] or not results['ids'][0]:
            # Nessun risultato trovato, restituisce una risposta valida ma vuota
            return json.dumps({
                "status": "success",
                "query": query_text,
                "results_count": 0,
                "results": [],
                "message": "Nessun ticket trovato per la query specificata"
            }, ensure_ascii=False, indent=2)
        
        # itera attraverso tutti i risultati trovati
        for i, (ticket_id, distance, metadata, document) in enumerate(zip(
            results['ids'][0],
            results['distances'][0], # lista delle distanze ( 0 identico, 1 diverso)
            results['metadatas'][0], # metadati associati
            results['documents'][0]
        )):
            # Calcola similarità (ChromaDB usa distanza, noi vogliamo similarità)
            similarity = 1 - distance # similarità 1 = identici, similarità 0 = completamente diverso
            
            # Estrai informazioni dai metadati
            title = metadata.get('metadata_title', metadata.get('title', 'N/A'))
            company = metadata.get('metadata_company', metadata.get('company', 'N/A'))
            date = metadata.get('metadata_date', metadata.get('date', 'N/A'))
            original_id = metadata.get('metadata_original_id', metadata.get('original_id', 'N/A'))
            
            # Tronca il testo del documento per evitare output troppo lunghi
            document_preview = document[:300] + "..." if len(document) > 300 else document
            
            # Costruzione oggetto risultato
            formatted_result = {
                "rank": i + 1, # posizione nella classifica per similarità decrescente
                "ticket_id": ticket_id,
                "similarity_score": round(similarity, 3),
                "title": title,
                "company": company,
                "date": date,
                "original_id": original_id,
                "content_preview": document_preview,
                "metadata": metadata
            }
            
            formatted_results.append(formatted_result)
        
        # Prepara la risposta finale
        response = {
            "status": "success",
            "query": query_text,
            "results_count": len(formatted_results),
            "results": formatted_results
        }
                
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        
        error_response = {
            "status": "error",
            "query": query_text,
            "error": str(e),
            "error_type": type(e).__name__
        }
        
        return json.dumps(error_response, ensure_ascii=False, indent=2)