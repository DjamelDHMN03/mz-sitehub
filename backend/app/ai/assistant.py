"""
Orchestrateur MZ ASSISTANT (sections 61, 66, 69-70).

Flux d'une question :
1. `parse_intent()` (déterministe) essaie de reconnaître la commande.
2. Si reconnue -> exécute directement le tool correspondant, formate la
   réponse à partir de SA SEULE donnée renvoyée.
3. Si non reconnue -> réponse honnête ("je n'ai pas compris") plutôt que
   d'inventer. Le branchement vers un LLM pour les formulations libres est
   prévu (app/ai/provider.py) mais pas câblé ici faute de pouvoir tester un
   vrai modèle dans cet environnement (voir docs/ROADMAP.md).

Aucune branche de ce fichier ne laisse un texte libre remplacer une donnée
de la base — conforme à la section 66.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import tools
from app.ai.intent import (
    INTENT_CONTACT_ROLE_LOOKUP,
    INTENT_CONTRACTS_EXPIRING,
    INTENT_LIST_SITES_BY_STATUS,
    INTENT_LIST_SITES_BY_WILAYA,
    INTENT_LIST_SITES_MISSING_APS,
    INTENT_LIST_SITES_WITHOUT_GPS,
    INTENT_MAP_FILTER_HIDE,
    INTENT_MAP_FILTER_SHOW,
    INTENT_MISSING_DOCUMENTS,
    INTENT_SUMMARIZE_SITE,
    INTENT_UNKNOWN,
    parse_intent,
)

NOT_AVAILABLE_MESSAGE = "Information non disponible dans MZ BUILDING."


@dataclass
class AssistantAnswer:
    text: str
    data: dict | list | None
    intent_type: str
    requires_confirmation: bool = False


def _format_site_list(sites: list[dict], empty_message: str) -> str:
    if not sites:
        return empty_message
    return "\n".join(f"- {s['code']}" + (f" ({s['name']})" if s.get("name") else "") for s in sites)


async def answer_question(db: AsyncSession, question: str) -> AssistantAnswer:
    intent = parse_intent(question)

    if intent.type == INTENT_LIST_SITES_BY_STATUS:
        sites = await tools.tool_list_sites_by_status(db, intent.params["status"])
        return AssistantAnswer(
            text=_format_site_list(sites, f"Aucun site au statut {intent.params['status']}."),
            data=sites, intent_type=intent.type,
        )

    if intent.type == INTENT_LIST_SITES_BY_WILAYA:
        sites = await tools.tool_list_sites_by_wilaya(db, intent.params["wilaya"])
        return AssistantAnswer(
            text=_format_site_list(sites, f"Aucun site trouvé pour la wilaya {intent.params['wilaya']}."),
            data=sites, intent_type=intent.type,
        )

    if intent.type == INTENT_LIST_SITES_WITHOUT_GPS:
        sites = await tools.tool_list_sites_without_gps(db)
        return AssistantAnswer(
            text=_format_site_list(sites, "Tous les sites ont un GPS renseigné."),
            data=sites, intent_type=intent.type,
        )

    if intent.type == INTENT_LIST_SITES_MISSING_APS:
        sites = await tools.tool_list_sites_missing_aps(db, intent.params.get("wilaya"))
        return AssistantAnswer(
            text=_format_site_list(sites, "Aucun site sans APS trouvé."),
            data=sites, intent_type=intent.type,
        )

    if intent.type == INTENT_SUMMARIZE_SITE:
        summary = await tools.tool_summarize_site(db, intent.params["code"])
        if summary is None:
            return AssistantAnswer(text=NOT_AVAILABLE_MESSAGE, data=None, intent_type=intent.type)
        lines = [
            f"{summary['code']} — {summary['name'] or 'À COMPLÉTER'}",
            f"Statut : {summary['status']}",
            f"Propriétaire : {summary['owner_name'] or 'À COMPLÉTER'}",
            f"Organisme : {summary['organisme'] or 'À COMPLÉTER'}",
        ]
        if summary["observation"]:
            lines.append(f"Observation : {summary['observation']}")
        if summary["contacts"]:
            lines.append("Contacts : " + ", ".join(f"{c['name']} ({c['role'] or '?'})" for c in summary["contacts"]))
        return AssistantAnswer(text="\n".join(lines), data=summary, intent_type=intent.type)

    if intent.type == INTENT_MISSING_DOCUMENTS:
        result = await tools.tool_missing_documents(db, intent.params["code"])
        if result is None:
            return AssistantAnswer(text=NOT_AVAILABLE_MESSAGE, data=None, intent_type=intent.type)
        text = (
            f"Pour {result['code']}, il manque : {', '.join(result['missing'])}."
            if result["missing"]
            else f"Le dossier {result['code']} est complet."
        )
        return AssistantAnswer(text=text, data=result, intent_type=intent.type)

    if intent.type == INTENT_CONTRACTS_EXPIRING:
        contracts = await tools.tool_contracts_expiring(db)
        if not contracts:
            text = "Aucun contrat n'arrive à expiration dans les 60 prochains jours."
        else:
            text = "\n".join(f"- {c['site_code']} ({c['reference']}) : {c['date_expiration']}" for c in contracts)
        return AssistantAnswer(text=text, data=contracts, intent_type=intent.type)

    if intent.type == INTENT_CONTACT_ROLE_LOOKUP:
        contacts = await tools.tool_contact_role_lookup(db, intent.params["role"], intent.params.get("organisme"))
        if not contacts:
            return AssistantAnswer(text=NOT_AVAILABLE_MESSAGE, data=[], intent_type=intent.type)
        text = "\n".join(f"- {c['name']} ({c['site_code']})" for c in contacts)
        return AssistantAnswer(text=text, data=contacts, intent_type=intent.type)

    if intent.type in (INTENT_MAP_FILTER_SHOW, INTENT_MAP_FILTER_HIDE):
        # section 63 : l'IA transforme la demande en filtre cartographique.
        # L'exécution du filtre a lieu côté frontend (CartePage) — cette
        # réponse renvoie juste le filtre structuré à appliquer, jamais de
        # texte libre qui remplacerait ce paramétrage.
        verb = "Affichage" if intent.type == INTENT_MAP_FILTER_SHOW else "Masquage"
        filter_desc = intent.params.get("status") or intent.params.get("wilaya")
        return AssistantAnswer(
            text=f"{verb} des sites : {filter_desc} — ouvrez la carte pour voir le résultat.",
            data={"map_action": "show" if intent.type == INTENT_MAP_FILTER_SHOW else "hide", **intent.params},
            intent_type=intent.type,
        )

    return AssistantAnswer(
        text=(
            "Je n'ai pas compris cette demande. Essayez par exemple : "
            "\"sites bloqués\", \"résume AL6328\", \"contrats qui expirent bientôt\"."
        ),
        data=None,
        intent_type=INTENT_UNKNOWN,
    )
