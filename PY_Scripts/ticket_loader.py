import chromadb
import json
from typing import List, Dict
import os
from datetime import datetime

class TicketLoader:
    def __init__(self, persist_directory: str = "./ticket_DB"):
        """
        Inizializza il caricatore con database persistente
        
        Args: persist_directory: Directory dove salvare il database ChromaDB
        """
        # Crea la directory se non esiste
        os.makedirs(persist_directory, exist_ok=True)
        
        # Inizializza ChromaDB con persistenza
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Crea o ottieni la collezione
        self.collection = self.client.get_or_create_collection(
            name="tickets_support",
            metadata={"hnsw:space": "cosine"}  # Usa similarità coseno
        )
        
        print(f"Database inizializzato in: {os.path.abspath(persist_directory)}")
        print(f"Ticket già presenti nella collezione: {self.collection.count()}")
    
    def load_tickets_from_json(self, json_file_path: str):
        """
        Carica i ticket dal file JSON nel database
        
        Args:json_file_path: Percorso al file JSON con i ticket
        """
        print(f"Caricamento ticket da: {json_file_path}")
        
        try:
            # Leggi il file JSON
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Estrai i documenti
            if isinstance(data, dict) and 'documents' in data:
                tickets = data['documents']
            elif isinstance(data, list):
                tickets = data
            else:
                raise ValueError("Formato JSON non riconosciuto")
            
            print(f"Trovati {len(tickets)} ticket nel file")
            
            # Prepara i dati per ChromaDB
            documents = []  # Testi per la vettorizzazione
            metadatas = []  # Metadati aggiuntivi
            ids = []        # ID univoci
            
            for ticket in tickets:
                # Usa il campo 'text' per la vettorizzazione
                if 'text' not in ticket:
                    print(f"Saltato ticket senza campo 'text': {ticket.get('id', 'NO_ID')}")
                    continue
                
                # Aggiungi il testo
                documents.append(ticket['text'])
                
                # Prepara i metadati appiattendo i dict annidati
                metadata = {}
                for k, v in ticket.items():
                    if k == 'text':  # Salta il testo principale
                        continue
                    elif isinstance(v, dict):  # Appiattisci i dict annidati
                        for sub_k, sub_v in v.items():
                            metadata[sub_k] = str(sub_v) if sub_v is not None else None
                    else:
                        metadata[k] = str(v) if v is not None else None
                
                metadatas.append(metadata)
                
                # Usa l'ID del ticket o genera uno univoco
                ticket_id = ticket.get('id', f"ticket_{len(ids)}")
                ids.append(str(ticket_id))
            
            # Carica nel database
            print(f"Inserimento di {len(documents)} ticket in ChromaDB...")
            
            # ChromaDB ha un limite sul batch size, facciamo chunk se necessario
            batch_size = 500
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                
                batch_docs = documents[i:end_idx]
                batch_metas = metadatas[i:end_idx]
                batch_ids = ids[i:end_idx]
                
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                
                print(f"Processati {end_idx}/{len(documents)} ticket...")
            
            print(f"✅ Caricamento completato!")
            print(f"Totale ticket nel database: {self.collection.count()}")
            
        except FileNotFoundError:
            print(f"❌ File non trovato: {json_file_path}")
        except json.JSONDecodeError as e:
            print(f"❌ Errore nel parsing JSON: {e}")
        except Exception as e:
            print(f"❌ Errore durante il caricamento: {e}")
    
    def check_database_status(self):
        """
        Mostra lo stato del database
        """
        count = self.collection.count()
        print(f"\n📊 Stato Database:")
        print(f"   Ticket totali: {count}")
        
        if count > 0:
            # Mostra alcuni esempi
            sample = self.collection.get(limit=3)
            print(f"   Esempi di ID: {sample['ids'][:3]}")
    
    def search_similar_tickets(self, query_text: str, n_results: int = 5):
        """
        Cerca ticket simili (funzione di test)
        
        Args:
            query_text: Testo da cercare
            n_results: Numero di risultati da restituire
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        print(f"\n🔍 Risultati ricerca per: '{query_text[:50]}...'")
        for i, (id, distance, metadata) in enumerate(zip(
            results['ids'][0],
            results['distances'][0], 
            results['metadatas'][0]
        )):
            print(f"   {i+1}. ID: {id} (similarità: {1-distance:.3f})")
            print(f"      Titolo: {metadata.get('title', 'N/A')[:80]}...")
            print()


# Script di esempio per l'uso
if __name__ == "__main__":
    # Inizializza il caricatore
    loader = TicketLoader()
    
    json_file_path = "ticket_totali_chroma.json" #file dove sono contenuti i ticket
    
    # Carica i ticket
    loader.load_tickets_from_json(json_file_path)
    
    # Verifica lo stato
    loader.check_database_status()
    
    # Test di ricerca (opzionale)
    test_query = "la referenza diventa pari a 0, diversamente dal prezzo inserito nei listini"
    loader.search_similar_tickets(test_query)