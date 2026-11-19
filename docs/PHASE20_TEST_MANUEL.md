# Test manuel — Phase 20 (RAG)

## Ce qui est déjà validé ici (sans Ollama, sans Postgres)

Extraction PDF, chunking, similarité cosinus, classement par pertinence —
tous testés réellement contre de vrais PDF. Voir `docs/ROADMAP.md`.

## Ce qu'il reste à valider chez vous (nécessite Ollama démarré)

## 1. Démarrer Ollama et récupérer le modèle d'embedding

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.1:8b
```

## 2. Vérifier qu'Ollama répond aux embeddings

```bash
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```
Doit renvoyer un vecteur de 768 nombres.

## 3. Uploader un vrai PDF avec du texte (pas un scan image)

```bash
SITE_ID="<id d'un site>"
curl -X POST "http://localhost:8000/sites/$SITE_ID/documents?category=CONTRATS" \
  -H "Authorization: Bearer $TOKEN" -F "file=@un_vrai_contrat.pdf"
```

## 4. Indexer ce document

```bash
DOC_ID="<id renvoyé à l'étape 3>"
curl -X POST http://localhost:8000/rag/documents/$DOC_ID/index \
  -H "Authorization: Bearer $TOKEN"
```
Doit renvoyer `chunks_created > 0`. Si erreur de connexion, vérifiez
`OLLAMA_BASE_URL` dans `.env` (doit pointer vers `http://ollama:11434`
depuis le conteneur backend, ou vers votre machine si Ollama tourne hors
Docker — voir la remarque sur le déploiement en Phase 19).

## 5. Rechercher

```bash
curl -X POST http://localhost:8000/rag/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "quelles sont les obligations du propriétaire", "top_k": 3}'
```
Vérifiez que chaque résultat a bien un `document_filename` et un
`page_number` — pas de résultat "orphelin" sans source.

## 6. Interface web

http://localhost:5173/documents → icône ✨ sur un PDF → indexation.
http://localhost:5173/assistant → cocher "Rechercher dans les documents" →
poser une question sur le contenu du PDF → vérifier que la citation de
source s'affiche sous chaque résultat.

## 7. Si le format de tool_calls d'Ollama ne correspond pas

Ce n'est pas utilisé dans cette phase (le RAG n'a pas besoin de function
calling, juste d'embeddings) — donc cette limite ne s'applique qu'à la
Phase 19. Le RAG devrait fonctionner dès qu'Ollama répond aux deux
commandes `curl` ci-dessus.

---

Dites-moi le résultat — j'enchaîne avec la Phase 21 (Sécurité) ensuite,
qui ne dépend d'aucun LLM et sera donc entièrement vérifiable statiquement.
