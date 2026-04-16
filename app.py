# Active les annotations différées pour éviter certains problèmes quand un type
# est utilisé avant sa définition effective.
from __future__ import annotations
# Importe le décorateur lru_cache pour mémoriser le graphe RDF après le premier chargement.
from functools import lru_cache
# Importe Path pour manipuler proprement les chemins de fichiers et dossiers.
from pathlib import Path
# Importe des types utiles pour annoter clairement les fonctions et variables.
from typing import Any, Dict, List, Optional, Set
# Importe depuis Flask :
# - Flask pour créer l'application web,
# - jsonify pour retourner des réponses JSON,
# - render_template pour afficher une page HTML,
# - request pour lire les données envoyées par le navigateur,
# - send_file pour permettre le téléchargement du fichier RDF.
from flask import Flask, jsonify, render_template, request, send_file
# Importe depuis rdflib :
# - Graph pour charger et interroger le fichier RDF,
# - Literal pour reconnaître les littéraux RDF,
# - URIRef pour reconnaître les URI RDF.
from rdflib import Graph, Literal, URIRef
# Importe les espaces de noms RDF/OWL standards.
from rdflib.namespace import OWL, RDF
# Définit le dossier de base du projet comme étant le dossier contenant ce fichier Python.
BASE_DIR = Path(__file__).resolve().parent
# Définit le chemin du fichier RDF que l'application doit charger.
ONTO_FILE = BASE_DIR / "diagnostic_informatique_swrl.rdf"
# Crée l'application Flask.
app = Flask(__name__)
# Définit une fonction utilitaire pour rendre un nom plus lisible à l'affichage.
def pretty(name: str) -> str:
    # Remplace les underscores par des espaces, enlève les espaces inutiles,
    # puis met la première lettre en majuscule.
    return name.replace("_", " ").strip().capitalize()
# Définit une fonction qui extrait le nom local d'une URI ou d'une valeur RDF.
def local_name(value: URIRef | Literal | str) -> str:
    # Convertit la valeur reçue en texte.
    text = str(value)
    # Vérifie si l'URI contient un dièse '#'.
    if "#" in text:
        # Si oui, retourne la partie située après le dernier '#'.
        return text.rsplit("#", 1)[1]
    # Sinon, retourne la partie située après le dernier '/'.
    return text.rsplit("/", 1)[-1]
# Mémorise le résultat de cette fonction pour éviter de recharger le fichier à chaque appel.
@lru_cache(maxsize=1)
# Définit une fonction qui charge le graphe RDF une seule fois.
def load_graph() -> Graph:
    # Vérifie que le fichier RDF existe bien.
    if not ONTO_FILE.exists():
        # Si le fichier n'existe pas, lève une erreur explicite.
        raise FileNotFoundError(f"Fichier RDF introuvable : {ONTO_FILE}")
    # Crée un graphe RDF vide.
    graph = Graph()
    # Charge le contenu du fichier RDF dans le graphe.
    graph.parse(ONTO_FILE)
    # Retourne le graphe chargé.
    return graph
# Définit une fonction qui recherche une URI dans le graphe à partir de son nom local.
def find_uri_by_local_name(graph: Graph, name: str) -> Optional[URIRef]:
    # Parcourt tous les sujets du graphe.
    for subject in graph.subjects():
        # Vérifie que le sujet est bien une URI et que son nom local correspond au nom cherché.
        if isinstance(subject, URIRef) and local_name(subject) == name:
            # Retourne cette URI dès qu'elle est trouvée.
            return subject
    # Parcourt tous les prédicats du graphe.
    for predicate in graph.predicates():
        # Vérifie que le prédicat est bien une URI et que son nom local correspond au nom cherché.
        if isinstance(predicate, URIRef) and local_name(predicate) == name:
            # Retourne cette URI dès qu'elle est trouvée.
            return predicate
    # Parcourt tous les objets du graphe.
    for obj in graph.objects():
        # Vérifie que l'objet est bien une URI et que son nom local correspond au nom cherché.
        if isinstance(obj, URIRef) and local_name(obj) == name:
            # Retourne cette URI dès qu'elle est trouvée.
            return obj
    # Retourne None si aucune URI correspondante n'a été trouvée.
    return None
# Définit une fonction qui récupère tous les individus appartenant à une classe donnée.
def class_members(graph: Graph, class_name: str) -> List[URIRef]:
    # Recherche l'URI correspondant au nom de la classe.
    class_uri = find_uri_by_local_name(graph, class_name)
    # Vérifie si la classe a été trouvée.
    if class_uri is None:
        # Retourne une liste vide si la classe n'existe pas dans le graphe.
        return []
    # Récupère tous les sujets dont le type RDF est cette classe.
    members = [subject for subject in graph.subjects(RDF.type, class_uri) if isinstance(subject, URIRef)]
    # Retourne la liste triée par nom local alphabétique.
    return sorted(members, key=lambda uri: local_name(uri).lower())
# Définit une fonction qui récupère les valeurs d'une propriété objet pour un sujet donné.
def object_values(graph: Graph, subject_name: str, property_name: str) -> List[str]:
    # Recherche l'URI du sujet à partir de son nom local.
    subject_uri = find_uri_by_local_name(graph, subject_name)
    # Recherche l'URI de la propriété à partir de son nom local.
    property_uri = find_uri_by_local_name(graph, property_name)
    # Vérifie si le sujet ou la propriété n'ont pas été trouvés.
    if subject_uri is None or property_uri is None:
        # Retourne une liste vide si l'un des deux manque.
        return []
    # Récupère les objets liés au sujet par cette propriété, puis extrait leur nom local.
    values = [local_name(obj) for obj in graph.objects(subject_uri, property_uri) if isinstance(obj, URIRef)]
    # Retourne les valeurs sans doublons et triées.
    return sorted(set(values))
# Définit une fonction qui récupère les valeurs d'une propriété de données pour un sujet donné.
def data_values(graph: Graph, subject_name: str, property_name: str) -> List[str]:
    # Recherche l'URI du sujet à partir de son nom local.
    subject_uri = find_uri_by_local_name(graph, subject_name)
    # Recherche l'URI de la propriété à partir de son nom local.
    property_uri = find_uri_by_local_name(graph, property_name)
    # Vérifie si le sujet ou la propriété n'ont pas été trouvés.
    if subject_uri is None or property_uri is None:
        # Retourne une liste vide si l'un des deux manque.
        return []
    # Récupère les objets associés à cette propriété et les convertit en chaînes de caractères.
    values = [str(obj) for obj in graph.objects(subject_uri, property_uri)]
    # Retourne les valeurs sans doublons et triées.
    return sorted(set(values))
# Définit une fonction qui retourne le catalogue des symptômes présents dans le RDF.
def symptoms_catalog() -> List[Dict[str, str]]:
    # Charge le graphe RDF.
    graph = load_graph()
    # Construit une liste de dictionnaires contenant le nom brut et le nom lisible de chaque symptôme.
    return [{"name": local_name(uri), "pretty": pretty(local_name(uri))} for uri in class_members(graph, "Symptome")]
# Définit une fonction qui retourne la liste des ordinateurs présents dans le RDF.
def existing_computers() -> List[Dict[str, Any]]:
    # Charge le graphe RDF.
    graph = load_graph()
    # Initialise une liste vide pour stocker les ordinateurs.
    computers: List[Dict[str, Any]] = []
    # Parcourt tous les individus de la classe Ordinateur.
    for uri in class_members(graph, "Ordinateur"):
        # Extrait le nom local de l'ordinateur.
        name = local_name(uri)
        # Ajoute un dictionnaire décrivant cet ordinateur dans la liste.
        computers.append(
            {
                # Stocke le nom brut de l'ordinateur.
                "name": name,
                # Stocke le nom lisible de l'ordinateur.
                "pretty": pretty(name),
                # Récupère et concatène les valeurs de la propriété a_marque.
                "marque": ", ".join(data_values(graph, name, "a_marque")),
                # Récupère et concatène les valeurs de la propriété a_etat.
                "etat": ", ".join(data_values(graph, name, "a_etat")),
                # Récupère et concatène les valeurs de la propriété a_type.
                "type": ", ".join(data_values(graph, name, "a_type")),
            }
        )
    # Retourne la liste complète des ordinateurs.
    return computers
# Définit la fonction principale qui infère un diagnostic à partir d'une liste de symptômes.
def infer_for_symptoms(symptom_names: List[str], nom_pc: str) -> Dict[str, Any]:
    # Charge le graphe RDF.
    graph = load_graph()
    # Construit l'ensemble des symptômes disponibles dans le fichier RDF.
    available_symptoms = {item["name"] for item in symptoms_catalog()}
    # Nettoie la liste reçue en gardant uniquement les symptômes valides, sans doublons, puis les trie.
    cleaned_symptoms = sorted({name for name in symptom_names if name in available_symptoms})
    # Vérifie si aucun symptôme valide n'a été fourni.
    if not cleaned_symptoms:
        # Retourne une réponse vide avec un message d'erreur explicite.
        return {
            # Retourne le nom du PC fourni, ou un nom par défaut.
            "nom_pc": nom_pc or "PC_temporaire",
            # Retourne la liste brute des symptômes vide.
            "symptomes": [],
            # Retourne la liste lisible des symptômes vide.
            "symptomes_pretty": [],
            # Retourne la liste des diagnostics vide.
            "diagnostics": [],
            # Retourne la liste lisible des diagnostics vide.
            "diagnostics_pretty": [],
            # Retourne la liste des solutions vide.
            "solutions": [],
            # Retourne la liste lisible des solutions vide.
            "solutions_pretty": [],
            # Indique le moteur logique utilisé.
            "engine": "Inférence relationnelle RDF",
            # Fournit le message d'erreur.
            "error": "Veuillez sélectionner au moins un symptôme valide du fichier RDF.",
        }
    # Crée un ensemble vide pour stocker les diagnostics sans doublons.
    diagnostics: Set[str] = set()
    # Crée un ensemble vide pour stocker les solutions sans doublons.
    solutions: Set[str] = set()
    # Parcourt chaque symptôme sélectionné.
    for symptom_name in cleaned_symptoms:
        # Récupère les diagnostics suggérés par ce symptôme.
        symptom_diagnostics = object_values(graph, symptom_name, "suggere")
        # Ajoute ces diagnostics dans l'ensemble global des diagnostics.
        diagnostics.update(symptom_diagnostics)
        # Parcourt chaque diagnostic trouvé.
        for diagnostic_name in symptom_diagnostics:
            # Ajoute les solutions liées à ce diagnostic dans l'ensemble global des solutions.
            solutions.update(object_values(graph, diagnostic_name, "corrige_par"))
    # Trie les diagnostics trouvés.
    diagnostics_sorted = sorted(diagnostics)
    # Trie les solutions trouvées.
    solutions_sorted = sorted(solutions)
    # Retourne le résultat final de l'inférence.
    return {
        # Retourne le nom du PC fourni, ou un nom par défaut.
        "nom_pc": nom_pc or "PC_temporaire",
        # Retourne la liste brute des symptômes retenus.
        "symptomes": cleaned_symptoms,
        # Retourne la version lisible des symptômes.
        "symptomes_pretty": [pretty(name) for name in cleaned_symptoms],
        # Retourne la liste brute des diagnostics.
        "diagnostics": diagnostics_sorted,
        # Retourne la version lisible des diagnostics.
        "diagnostics_pretty": [pretty(name) for name in diagnostics_sorted],
        # Retourne la liste brute des solutions.
        "solutions": solutions_sorted,
        # Retourne la version lisible des solutions.
        "solutions_pretty": [pretty(name) for name in solutions_sorted],
        # Indique le moteur logique utilisé.
        "engine": "Inférence relationnelle RDF",
        # Retourne None s'il y a des diagnostics, sinon un message d'erreur.
        "error": None if diagnostics_sorted else "Aucun diagnostic n'a été trouvé à partir des relations présentes dans le RDF.",
    }
# Définit une fonction qui fait l'inférence à partir d'un ordinateur déjà existant dans le RDF.
def infer_for_existing_pc(pc_name: str) -> Dict[str, Any]:
    # Charge le graphe RDF.
    graph = load_graph()
    # Construit l'ensemble des noms d'ordinateurs existants.
    computer_names = {item["name"] for item in existing_computers()}
    # Vérifie si l'ordinateur demandé n'existe pas.
    if pc_name not in computer_names:
        # Retourne une réponse d'erreur.
        return {
            # Retourne le nom demandé.
            "nom_pc": pc_name,
            # Retourne une liste vide de symptômes.
            "symptomes": [],
            # Retourne une liste vide de symptômes lisibles.
            "symptomes_pretty": [],
            # Retourne une liste vide de diagnostics.
            "diagnostics": [],
            # Retourne une liste vide de diagnostics lisibles.
            "diagnostics_pretty": [],
            # Retourne une liste vide de solutions.
            "solutions": [],
            # Retourne une liste vide de solutions lisibles.
            "solutions_pretty": [],
            # Indique le moteur logique utilisé.
            "engine": "Inférence relationnelle RDF",
            # Fournit le message d'erreur.
            "error": "Ordinateur introuvable dans le fichier RDF.",
        }
    # Récupère les symptômes associés à cet ordinateur dans le RDF.
    symptoms = object_values(graph, pc_name, "a_symptome")

    # Réutilise la fonction d'inférence générale avec les symptômes trouvés.
    return infer_for_symptoms(symptoms, pc_name)
# Associe cette fonction à la route principale '/' avec les méthodes GET et POST.
@app.route("/", methods=["GET", "POST"])
# Définit la vue principale de l'application.
def index():
    # Initialise le résultat à None avant tout traitement.
    result = None
    # Initialise la liste des symptômes sélectionnés.
    selected: List[str] = []
    # Initialise le mode par défaut sur "personnalise".
    mode = "personnalise"
    # Initialise le nom de l'ordinateur existant sélectionné.
    selected_pc = ""
    # Initialise le nom par défaut du PC pour le mode personnalisé.
    nom_pc = "PC_TP_BAC3"
    # Vérifie si le formulaire a été soumis en POST.
    if request.method == "POST":
        # Lit le mode choisi dans le formulaire.
        mode = request.form.get("mode", "personnalise")
        # Vérifie si l'utilisateur a choisi le mode PC existant.
        if mode == "pc_existant":
            # Récupère le nom du PC sélectionné.
            selected_pc = request.form.get("pc_name", "")
            # Lance l'inférence pour ce PC existant.
            result = infer_for_existing_pc(selected_pc)
            # Récupère les symptômes du résultat pour les réafficher dans la page.
            selected = result["symptomes"]
            # Récupère le nom du PC depuis le résultat.
            nom_pc = result["nom_pc"]
        else:
            # Récupère la liste des symptômes cochés dans le formulaire.
            selected = request.form.getlist("symptomes")
            # Récupère le nom saisi pour le PC, ou utilise une valeur par défaut.
            nom_pc = request.form.get("nom_pc", "").strip() or "PC_TP_BAC3"
            # Lance l'inférence à partir des symptômes sélectionnés.
            result = infer_for_symptoms(selected, nom_pc)
    # Retourne la page HTML avec toutes les données nécessaires.
    return render_template(
        # Indique le template HTML à afficher.
        "index.html",
        # Passe le nom du fichier RDF au template.
        onto_filename=ONTO_FILE.name,
        # Passe la liste des symptômes disponibles.
        symptoms=symptoms_catalog(),
        # Passe la liste des ordinateurs existants.
        computers=existing_computers(),
        # Passe le résultat du diagnostic.
        result=result,
        # Passe les symptômes sélectionnés.
        selected=selected,
        # Passe le mode courant.
        mode=mode,
        # Passe le PC existant sélectionné.
        selected_pc=selected_pc,
        # Passe le nom du PC courant.
        nom_pc=nom_pc,
    )
# Associe cette fonction à la route '/api'.
@app.route("/api")
# Définit une route d'aide pour l'API.
def api_help():
    # Retourne des informations d'aide au format JSON.
    return jsonify(
        {
            # Décrit brièvement comment utiliser l'API.
            "message": "Envoyer un POST JSON sur /api/diagnostiquer",
            # Indique le fichier d'ontologie actuellement utilisé.
            "ontology_file": ONTO_FILE.name,
            # Indique le moteur logique utilisé.
            "engine": "Inférence relationnelle RDF",
            # Liste les routes disponibles dans l'application.
            "routes": ["/", "/api", "/api/diagnostiquer", "/api/symptomes", "/api/ordinateurs", "/ontology"],
            # Donne un exemple de charge utile JSON.
            "example_payload": {"nom_pc": "PC_API", "symptomes": ["ecran_noir", "bips"]},
        }
    )
# Associe cette fonction à la route '/api/symptomes'.
@app.route("/api/symptomes")
# Définit une route qui retourne la liste des symptômes.
def api_symptoms():
    # Retourne les symptômes au format JSON.
    return jsonify(symptoms_catalog())
# Associe cette fonction à la route '/api/ordinateurs'.
@app.route("/api/ordinateurs")
# Définit une route qui retourne la liste des ordinateurs.
def api_computers():
    # Retourne les ordinateurs au format JSON.
    return jsonify(existing_computers())
# Associe cette fonction à la route '/api/diagnostiquer' avec la méthode POST.
@app.route("/api/diagnostiquer", methods=["POST"])
# Définit la route API principale pour lancer un diagnostic.
def api_diagnostiquer():
    # Lit le contenu JSON envoyé dans la requête ;
    # force=True demande à Flask d'essayer de lire en JSON,
    # silent=True évite une exception si le JSON est absent ou invalide.
    payload = request.get_json(force=True, silent=True) or {}
    # Récupère le nom du PC depuis le JSON ou utilise "PC_API" par défaut.
    nom_pc = str(payload.get("nom_pc", "PC_API"))
    # Récupère la liste des symptômes envoyés dans le JSON.
    symptomes = payload.get("symptomes", [])
    # Vérifie que la valeur reçue est bien une liste.
    if not isinstance(symptomes, list):
        # Remplace par une liste vide si ce n'est pas une liste.
        symptomes = []
    # Retourne le résultat du diagnostic au format JSON.
    return jsonify(infer_for_symptoms([str(item) for item in symptomes], nom_pc))
# Associe cette fonction à la route '/ontology'.
@app.route("/ontology")
# Définit une route pour télécharger le fichier RDF.
def download_ontology():
    # Vérifie si le fichier RDF existe.
    if not ONTO_FILE.exists():
        # Retourne une erreur JSON 404 si le fichier est introuvable.
        return jsonify({"error": f"Fichier introuvable : {ONTO_FILE.name}"}), 404
    # Envoie le fichier RDF au navigateur en téléchargement.
    return send_file(ONTO_FILE, as_attachment=True, download_name=ONTO_FILE.name)
# Vérifie que ce fichier est exécuté directement et non importé depuis un autre script.
if __name__ == "__main__":
    # Lance l'application Flask en mode debug.
    app.run(debug=True)