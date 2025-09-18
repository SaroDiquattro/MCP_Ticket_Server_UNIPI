import chromadb
import pandas as pd
from sklearn.manifold import TSNE
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors
import argparse
import sys
from pathlib import Path

def load_chroma_data(db_path, collection_name):
    """
    Carica i dati da ChromaDB
    """
    try:
        client = chromadb.PersistentClient(path=db_path)
        
        # Test connessione
        heartbeat = client.heartbeat()
        if heartbeat == 0:
            print("❌ Errore di connessione a ChromaDB!")
            return None, None
        
        print(f"✅ Connessione a ChromaDB riuscita! (heartbeat: {heartbeat})")
        
        # Ottieni la collezione
        try:
            collection = client.get_collection(name=collection_name)
        except:
            print(f"❌ Collezione '{collection_name}' non trovata!")
            print("Collezioni disponibili:")
            for coll in client.list_collections():
                print(f"  - {coll.name}")
            return None, None
        
        print(f"📊 Record totali nella collezione '{collection_name}': {collection.count()}")
        
        return client, collection
        
    except Exception as e:
        print(f"❌ Errore nel caricamento dei dati: {e}")
        return None, None

def get_embeddings_data(collection, limit=None):
    """
    Estrae tutti gli embeddings dalla collezione
    """
    try:
        # Se non è specificato un limite, prendi tutti i record
        if limit is None:
            limit = collection.count()
        
        print(f"🔄 Caricamento di {limit} record...")
        
        # Ottieni tutti i dati
        data = collection.get(limit=limit, include=["embeddings", "documents", "metadatas"])
        
        # FIX: Controlla se la lista embeddings è vuota o None
        if data['embeddings'] is None or len(data['embeddings']) == 0:
            print("❌ Nessun embedding trovato nella collezione!")
            return None
        
        print(f"✅ Caricati {len(data['embeddings'])} embeddings")
        
        # FIX: Crea il DataFrame senza gli embeddings prima
        df_data = {
            'ids': data['ids'],
            'documents': data['documents'] if data['documents'] else [''] * len(data['ids']),
            'metadatas': data['metadatas'] if data['metadatas'] else [{}] * len(data['ids'])
        }
        
        df = pd.DataFrame(df_data)
        
        # FIX: Aggiungi gli embeddings come liste Python, non numpy arrays
        embeddings_as_lists = [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in data['embeddings']]
        df['embeddings'] = embeddings_as_lists
        
        print(f"📐 Dimensione primo embedding: {len(embeddings_as_lists[0]) if embeddings_as_lists else 0}")
        
        return df
        
    except Exception as e:
        print(f"❌ Errore nell'estrazione degli embeddings: {e}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return None

def create_tsne_visualization(df, perplexity=30, n_components=2, random_state=42, 
                            learning_rate=200, max_iter=1000):
    """
    Crea la visualizzazione t-SNE degli embeddings
    """
    try:
        print("🔄 Creazione della visualizzazione t-SNE...")
        
        # Converti embeddings in matrice numpy
        print("🔄 Conversione embeddings in matrice numpy...")
        embeddings_list = df['embeddings'].tolist()
        matrix = np.array(embeddings_list, dtype=np.float32)
        print(f"📐 Dimensioni matrice embeddings: {matrix.shape}")
        
        # Verifica che la matrice sia valida
        if matrix.shape[0] == 0:
            print("❌ Matrice embeddings vuota!")
            return None
            
        if np.any(np.isnan(matrix)):
            print("⚠️ Trovati valori NaN nella matrice embeddings, li sostituisco con 0")
            matrix = np.nan_to_num(matrix)
        
        # Ajusta perplexity se necessario (deve essere minore del numero di campioni)
        n_samples = matrix.shape[0]
        if perplexity >= n_samples:
            perplexity = min(30, max(5, n_samples // 4))
            print(f"⚠️  Perplexity ajustada a {perplexity} per {n_samples} campioni")
        
        # Crea modello t-SNE
        print(f"🔄 Inizializzazione t-SNE con perplexity={perplexity}...")
        tsne = TSNE(
            n_components=n_components,
            perplexity=perplexity,
            random_state=random_state,
            learning_rate=learning_rate,
            max_iter=max_iter,
            verbose=1
        )
        
        # Trasforma i dati
        print("🔄 Esecuzione t-SNE...")
        vis_dims = tsne.fit_transform(matrix)
        print(f"✅ t-SNE completato! Dimensioni output: {vis_dims.shape}")
        
        return vis_dims
        
    except Exception as e:
        print(f"❌ Errore nella creazione del t-SNE: {e}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return None

def plot_tsne_results(df, vis_dims, save_path="chroma_tsne_visualization.png", 
                     show_labels=True, label_sample_size=100, figsize=(20, 15)):
    """
    Crea il grafico della visualizzazione t-SNE e lo salva come PNG
    """
    try:
        print("🎨 Creazione del grafico...")
        
        # Configura matplotlib per output di alta qualità
        plt.rcParams['figure.dpi'] = 300
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['font.size'] = 10
        
        # Estrai coordinate
        x = vis_dims[:, 0]
        y = vis_dims[:, 1]
        
        # Crea figura
        fig, ax = plt.subplots(figsize=figsize)
        
        # Crea colori casuali per i punti
        np.random.seed(42)  # Per risultati riproducibili
        n_points = len(x)
        colors = plt.cm.Set3(np.random.rand(n_points))
        
        # Scatter plot
        scatter = ax.scatter(x, y, c=colors, alpha=0.7, s=30, edgecolors='black', linewidth=0.5)
        
        # Aggiungi etichette (solo per un campione se ci sono troppi punti)
        if show_labels and len(df) > 0:
            # Se ci sono troppi punti, mostra solo un campione
            if len(df) > label_sample_size:
                # Prendi punti distribuiti uniformemente invece che casuali
                step = len(df) // label_sample_size
                sample_indices = range(0, len(df), step)[:label_sample_size]
                print(f"📝 Mostrando etichette per {len(sample_indices)} punti distribuiti")
            else:
                sample_indices = range(len(df))
                print(f"📝 Mostrando etichette per tutti i {len(sample_indices)} punti")
            
            for i in sample_indices:
                if i < len(vis_dims) and i < len(df):
                    # Usa il documento come etichetta, troncandolo se troppo lungo
                    doc = df.iloc[i]['documents']
                    label = str(doc) if doc is not None else f"Doc_{i}"
                    if len(label) > 40:
                        label = label[:37] + "..."
                    
                    a, b = vis_dims[i, :]
                    ax.annotate(label, (a, b), xytext=(3, 3), 
                               textcoords="offset points", ha="left", va="bottom",
                               fontsize=8, alpha=0.8, 
                               bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))
        
        # Personalizza il grafico
        ax.set_title(f"Visualizzazione t-SNE degli Embeddings ChromaDB\n{len(df)} documenti", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("t-SNE Dimensione 1", fontsize=12)
        ax.set_ylabel("t-SNE Dimensione 2", fontsize=12)
        
        # Aggiungi griglia
        ax.grid(True, alpha=0.3)
        
        # Migliora il layout
        plt.tight_layout()
        
        # Salva il grafico
        print(f"💾 Salvando il grafico come: {save_path}")
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        
        print(f"✅ Grafico salvato con successo!")
        
        # Mostra anche il grafico (se possibile)
        try:
            plt.show()
        except:
            print("ℹ️  Grafico salvato ma non visualizzabile in questo ambiente")
        
        plt.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore nella creazione del grafico: {e}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return False

def main():
    """
    Funzione principale
    """
    parser = argparse.ArgumentParser(description="Visualizza embeddings ChromaDB con t-SNE")
    parser.add_argument("--db_path", default="./data", help="Percorso del database ChromaDB")
    parser.add_argument("--collection", default="default", help="Nome della collezione")
    parser.add_argument("--limit", type=int, help="Limite di record da processare (default: tutti)")
    parser.add_argument("--perplexity", type=int, default=30, help="Perplexity per t-SNE")
    parser.add_argument("--output", default="chroma_tsne_visualization.png", help="Nome file output")
    parser.add_argument("--no-labels", action="store_true", help="Non mostrare le etichette")
    parser.add_argument("--label-sample", type=int, default=100, help="Numero max di etichette da mostrare")
    
    args = parser.parse_args()
    
    print("🚀 ChromaDB t-SNE Visualizer")
    print("="*50)
    
    # Carica i dati
    client, collection = load_chroma_data(args.db_path, args.collection)
    if collection is None:
        sys.exit(1)
    
    # Estrai embeddings
    df = get_embeddings_data(collection, args.limit)
    if df is None:
        sys.exit(1)
    
    # Crea visualizzazione t-SNE
    vis_dims = create_tsne_visualization(df, perplexity=args.perplexity)
    if vis_dims is None:
        sys.exit(1)
    
    # Crea e salva il grafico
    success = plot_tsne_results(
        df, vis_dims, 
        save_path=args.output,
        show_labels=not args.no_labels,
        label_sample_size=args.label_sample
    )
    
    if success:
        print("="*50)
        print(f"🎉 Processo completato! Controlla il file: {args.output}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()