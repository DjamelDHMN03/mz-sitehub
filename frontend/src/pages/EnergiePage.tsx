async function handleAddPaiement(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    setSavingPaiement(true);
    setStatusMsg("");
    setErrorMsg("");
    try {
      const payload = {
        mois: normalizeMois(mois),
        date_paiement: toDateInput(datePaiement),
        montant: Number(montant),
        observation: obsPaiement.trim() ? obsPaiement.trim() : null,
      };
      await api.post(
        `/api/energie/sites/${encodeURIComponent(selectedId)}/paiements`,
        payload
      );
      setObsPaiement("");
      await chargerPaiements(selectedId);
      setStatusMsg("Paiement enregistré.");
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Échec de l'ajout du paiement.");
    } finally {
      setSavingPaiement(false);
    }
  }
