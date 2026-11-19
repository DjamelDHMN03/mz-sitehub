"""
Routeur Contrats (sections 35-36).

Rappel de la règle transversale du projet (section 74) : montant, dates,
statut juridique et pouvoir de signature ne sont JAMAIS déduits ou estimés
par le backend — ils restent `null` tant que l'utilisateur ne les a pas
saisis explicitement. Aucune valeur par défaut "raisonnable" n'est appliquée
ici (pas de `duration_years` par défaut, pas de statut initial imposé).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.tracking import Contract, ContractSignatory
from app.models.user import User
from app.schemas.contract import (
    VALID_SIGNATORY_PARTIES,
    ContractCreate,
    ContractOut,
    ContractUpdate,
    SignatoryCreate,
    SignatoryOut,
    SignatoryUpdate,
)

router = APIRouter(tags=["contracts"])


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    return site


async def _get_contract_or_404(db: AsyncSession, contract_id: uuid.UUID) -> Contract:
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrat introuvable")
    return contract


@router.post("/sites/{site_id}/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    site_id: uuid.UUID,
    payload: ContractCreate,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    await _get_site_or_404(db, site_id)
    now = datetime.now(timezone.utc)
    contract = Contract(site_id=site_id, created_at=now, updated_at=now, **payload.model_dump())
    db.add(contract)
    await db.flush()

    await log_audit(
        db, user_id=current_user.id, entity="contracts", entity_id=contract.id,
        action="CREATE", new_value=contract.reference,
    )
    await db.commit()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.get("/sites/{site_id}/contracts", response_model=list[ContractOut])
async def list_site_contracts(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContractOut]:
    result = await db.execute(
        select(Contract)
        .where(Contract.site_id == site_id, Contract.deleted_at.is_(None))
        .order_by(Contract.created_at.desc())
    )
    return [ContractOut.model_validate(c) for c in result.scalars().all()]


@router.get("/contracts/expiring-soon", response_model=list[ContractOut])
async def list_expiring_contracts(
    within_days: int = 60,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContractOut]:
    """Section 96/72 : contrats proches de l'expiration — utile pour
    l'assistant IA et les rapports (bases posées ici, exploitées en Phase 19)."""
    from datetime import date, timedelta

    limit_date = date.today() + timedelta(days=within_days)
    result = await db.execute(
        select(Contract).where(
            Contract.deleted_at.is_(None),
            Contract.date_expiration.is_not(None),
            Contract.date_expiration <= limit_date,
            Contract.date_expiration >= date.today(),
        )
    )
    return [ContractOut.model_validate(c) for c in result.scalars().all()]


@router.patch("/contracts/{contract_id}", response_model=ContractOut)
async def update_contract(
    contract_id: uuid.UUID,
    payload: ContractUpdate,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    contract = await _get_contract_or_404(db, contract_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, new_value in changes.items():
        old_value = getattr(contract, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="contracts", entity_id=contract.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(contract, field, new_value)

    contract.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    contract = await _get_contract_or_404(db, contract_id)
    contract.deleted_at = datetime.now(timezone.utc)
    await log_audit(db, user_id=current_user.id, entity="contracts", entity_id=contract.id, action="DELETE")
    await db.commit()


# ------------------------------------------------------------------
# Signataires
# ------------------------------------------------------------------
@router.post(
    "/contracts/{contract_id}/signatories",
    response_model=SignatoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_signatory(
    contract_id: uuid.UUID,
    payload: SignatoryCreate,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> SignatoryOut:
    await _get_contract_or_404(db, contract_id)
    if payload.party not in VALID_SIGNATORY_PARTIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "party doit être PROPRIETAIRE ou OOREDOO")

    signatory = ContractSignatory(contract_id=contract_id, **payload.model_dump())
    db.add(signatory)
    await db.flush()

    await log_audit(
        db, user_id=current_user.id, entity="contract_signatories", entity_id=signatory.id,
        action="CREATE", new_value=signatory.name,
    )
    await db.commit()
    await db.refresh(signatory)
    return SignatoryOut.model_validate(signatory)


@router.get("/contracts/{contract_id}/signatories", response_model=list[SignatoryOut])
async def list_signatories(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SignatoryOut]:
    await _get_contract_or_404(db, contract_id)
    result = await db.execute(
        select(ContractSignatory).where(ContractSignatory.contract_id == contract_id)
    )
    return [SignatoryOut.model_validate(s) for s in result.scalars().all()]


@router.patch("/signatories/{signatory_id}", response_model=SignatoryOut)
async def update_signatory(
    signatory_id: uuid.UUID,
    payload: SignatoryUpdate,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> SignatoryOut:
    result = await db.execute(select(ContractSignatory).where(ContractSignatory.id == signatory_id))
    signatory = result.scalar_one_or_none()
    if signatory is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Signataire introuvable")

    changes = payload.model_dump(exclude_unset=True)
    for field, new_value in changes.items():
        old_value = getattr(signatory, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="contract_signatories", entity_id=signatory.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(signatory, field, new_value)

    await db.commit()
    await db.refresh(signatory)
    return SignatoryOut.model_validate(signatory)


@router.delete("/signatories/{signatory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_signatory(
    signatory_id: uuid.UUID,
    current_user: User = Depends(require_permission("contracts", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(ContractSignatory).where(ContractSignatory.id == signatory_id))
    signatory = result.scalar_one_or_none()
    if signatory is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Signataire introuvable")
    await log_audit(
        db, user_id=current_user.id, entity="contract_signatories", entity_id=signatory.id, action="DELETE"
    )
    await db.delete(signatory)
    await db.commit()
