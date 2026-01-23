#!/usr/bin/env python3
"""
NL2RDF - Convertisseur générique langage naturel → Graphe RDF
Utilise le système NL2SPARQL existant du projet avec Deepseek
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(Path(__file__).parent / '.env')

from querif.nl2sparql.main import generate_and_execute_query
from querif.rdf_graph_builder import RDFGraphBuilder


class NL2RDFConverter:
    """Convertisseur générique utilisant le système NL2SPARQL avec Deepseek"""
    
    def convert(self, question: str, max_results: int = 10, save_files: bool = True, verbose: bool = True):
        """Convertit une question en langage naturel en graphe RDF"""
        
        if verbose:
            print("\n" + "="*80)
            print("NL2RDF - CONVERTISSEUR GÉNÉRIQUE")
            print("="*80)
            print(f"\n📝 Question: {question}\n")
        
        try:
            # [1] Utiliser le système NL2SPARQL du projet avec Deepseek
            if verbose:
                print("[1] Conversion NL → SPARQL (Deepseek)...")
            
            sparql_query, results = generate_and_execute_query(question, config_key="DEEPSEEK")
            
            if not sparql_query:
                print("❌ Impossible de générer une requête SPARQL")
                return None
            
            if verbose:
                print("✓ Requête SPARQL générée")
                print("-"*80)
                for line in sparql_query.split('\n')[:5]:
                    if line.strip():
                        print(f"  {line}")
                print("  ...")
                print("-"*80)
            
            # [2] Vérifier les résultats
            if not results or 'results' not in results:
                print("❌ Aucun résultat")
                return None
            
            bindings = results['results'].get('bindings', [])
            if len(bindings) == 0:
                print("❌ Pas de résultats")
                return None
            
            if verbose:
                print(f"\n[2] Résultats: {len(bindings)} trouvé(s)\n")
                print("Exemples:")
                for i, binding in enumerate(bindings[:min(5, len(bindings))]):
                    print(f"  {i+1}. ", end="")
                    vals = [f"{v.get('value', 'N/A')[:40]}" for v in binding.values()]
                    print(" | ".join(vals))
                if len(bindings) > 5:
                    print(f"  ... et {len(bindings) - 5} autre(s)")
            
            # [3] Construire le graphe RDF
            if verbose:
                print(f"\n[3] Construction du graphe RDF (max: {max_results})...")
            
            rdf_graph = RDFGraphBuilder()
            rdf_graph.build_from_results(sparql_query, results, max_results=max_results)
            
            if verbose:
                rdf_graph.print_summary()
            
            # [4] Sauvegarder
            if save_files:
                safe_name = question.lower()[:40].replace(" ", "_").replace("?", "")
                ttl_file = f"{safe_name}_rdf.ttl"
                png_file = f"{safe_name}_rdf.png"
                
                if verbose:
                    print("\n[4] Sauvegarde...")
                
                rdf_graph.export_to_turtle(ttl_file)
                rdf_graph.visualize(filename=png_file, title=f"Graphe RDF: {question[:50]}")
                
                if verbose:
                    print(f"✓ {png_file}")
                    print(f"✓ {ttl_file}")
            
            if verbose:
                print("\n" + "="*80)
                print("✅ CONVERSION RÉUSSIE!")
                print("="*80 + "\n")
            
            return rdf_graph
            
        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    converter = NL2RDFConverter()
    
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        converter.convert(question, max_results=10)
    else:
        print("\n" + "="*80)
        print("NL2RDF - Convertisseur générique NL → Graphe RDF")
        print("="*80)
        print("""
Utilise le système NL2SPARQL du projet (Deepseek)

Exemples:
  python nl2rdf_converter.py "List Drake songs"
  python nl2rdf_converter.py "Movies directed by Steven Spielberg"
  python nl2rdf_converter.py "Where is Celine Dion born?"
  python nl2rdf_converter.py "Who is older, Obama or Trump?"
  python nl2rdf_converter.py "Capital of France"
  python nl2rdf_converter.py "How many albums did Adele release?"
""")
        print("="*80 + "\n")
