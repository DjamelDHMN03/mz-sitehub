# Test manuel — Phase 19 (Assistant IA)

## Ce qui est déjà validé (sans Docker, dans l'environnement de construction)

- Les 12 exemples exacts du cahier des charges (sections 62/63/69) sont
  reconnus correctement par `app/ai/intent.py`
- L'orchestrateur (`app/ai/assistant.py`) a été testé avec les tools mockés

## Ce qu'il reste à valider chez vous

## 1. Sans Ollama — le moteur à règles doit déjà fonctionner

```bash
curl -X POST http://localhost:8000/assistant/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "Sites bloqués"}'
```
Doit renvoyer une vraie liste de sites (ou "Aucun site au statut BLOQUE.")
— sans avoir besoin d'Ollama, car cette commande passe par le moteur à
règles déterministe.

## 2. Action avec confirmation

```bash
curl -X POST http://localhost:8000/assistant/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "Ajoute BENREGREG AMEUR comme DRH de AL6328."}'
```
Doit renvoyer `pending_action` sans rien avoir écrit en base. Vérifiez :
```bash
curl http://localhost:8000/sites/<AL6328_id>/contacts -H "Authorization: Bearer $TOKEN"
```
BENREGREG AMEUR ne doit PAS encore apparaître.

Puis confirmez :
```bash
curl -X POST http://localhost:8000/assistant/confirm-action \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action": "ADD_CONTACT", "params": {"name": "BENREGREG AMEUR", "role": "DRH", "code": "AL6328"}}'
```
Revérifiez la liste des contacts : BENREGREG AMEUR doit maintenant apparaître.

## 3. Anti-hallucination

```bash
curl -X POST http://localhost:8000/assistant/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "Résume SITE_QUI_N_EXISTE_PAS."}'
```
Doit renvoyer exactement "Information non disponible dans MZ SITEHUB."

## 4. Interface web

http://localhost:5173/assistant → cliquer une suggestion rapide → vérifier
la réponse → taper "Ajoute Test Nom comme DRH de <un vrai code>" → cliquer
Confirmer → vérifier dans Contacts que ça a bien été créé.

## 5. Quand vous aurez Ollama qui tourne (pour plus tard, pas urgent)

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1:8b
curl http://localhost:11434/api/chat -d '{"model":"llama3.1:8b","messages":[{"role":"user","content":"bonjour"}],"stream":false}'
```
Si cette commande fonctionne, `OllamaProvider` devrait fonctionner aussi —
mais il faudra vérifier concrètement le format de `tool_calls` renvoyé par
votre version d'Ollama/du modèle, qui peut différer légèrement de ce que
`provider.py` attend. Dites-le-moi à ce moment-là, je corrigerai sur la
base d'un vrai retour d'erreur plutôt qu'en devinant.

---

Dites-moi le résultat — j'enchaîne avec la Phase 20 (RAG) ensuite, en
gardant à l'esprit la même limite (pas d'Ollama testable ici).
