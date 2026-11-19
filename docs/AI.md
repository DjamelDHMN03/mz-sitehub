# AI.md — MZ SITEHUB, Assistant IA & RAG

## Deux couches, une seule garantie : jamais de donnée inventée

### 1. Moteur à règles (fonctionne sans Ollama, 0 DA garanti)

app/ai/intent.py reconnaît les commandes structurées du cahier des charges
(sites par statut/wilaya, résumé de site, documents manquants, contrats
expirants, recherche de contact par fonction, filtres carte, ajout de
contact avec confirmation). Testé réellement sur 12 exemples exacts + cas
limites (voir docs/TESTING.md).

### 2. LLM via Ollama (optionnel, étend la couverture aux formulations libres)

app/ai/provider.py définit une interface AIProvider — OllamaProvider
appelle un vrai serveur Ollama local (/api/chat, /api/embeddings). Non
activé par défaut nécessaire ; l'app fonctionne sans.

## Comment ça répond

```
Question utilisateur
      |
      v
parse_intent()  --- reconnue ---> tool_*() (requête DB réelle) --> réponse
      |
      +-- non reconnue --> "Je n'ai pas compris cette demande." (jamais d'invention)
```

Chaque tool_*() dans app/ai/tools.py va chercher la donnée en base — le
LLM (quand branché) ne fait que choisir QUEL tool appeler, jamais répondre
depuis sa propre "mémoire".

## Anti-hallucination

Si un site/contact n'existe pas : réponse exacte
"Information non disponible dans MZ SITEHUB." — jamais une réponse
approximative ou une extrapolation.

## Confirmation avant toute action

Une demande comme "Ajoute BENREGREG AMEUR comme DRH de AL6328" ne modifie
RIEN tant que l'utilisateur n'a pas cliqué "Confirmer" — voir
POST /assistant/chat (renvoie pending_action) puis
POST /assistant/confirm-action.

## RAG (recherche dans les documents)

```
PDF -> extraction texte (pypdf) -> découpage en chunks -> embeddings (Ollama)
    -> stockage pgvector -> recherche par similarité -> réponse AVEC citation
    (nom de fichier + numéro de page, toujours)
```

Nécessite Ollama démarré avec le modèle nomic-embed-text (embeddings).
Sans Ollama, le RAG renvoie une erreur explicite plutôt qu'un résultat
inventé.

## Configurer Ollama

Voir docs/DEPLOYMENT.md section 4, et docs/PHASE19_TEST_MANUEL.md /
docs/PHASE20_TEST_MANUEL.md pour les commandes de test pas à pas.

## Limite assumée

Le format exact de function-calling attendu par OllamaProvider.chat() n'a
pas pu être vérifié contre un vrai serveur Ollama dans l'environnement où
ce projet a été construit. Le moteur à règles ne dépend pas de ça et
fonctionne déjà ; ajustez provider.py sur la base d'un vrai message
d'erreur le jour où vous testerez avec Ollama réellement démarré.
