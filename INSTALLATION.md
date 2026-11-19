# MZ BUILDING — Installation et lancement sous Windows 11 (PowerShell)

Sans Docker. Une étape à la fois. Toutes les commandes se tapent dans **PowerShell**
(touche Windows, taper `PowerShell`, Entrée).

Dossier du projet utilisé dans ce guide :
`C:\Users\WINDOWS 11\OneDrive\Desktop\MZ-SITEHUB-COMPLET\MZ-SITEHUB`

## Lancement quotidien (une fois tout installé)

Double-cliquez sur **START_TOUT.bat** : il ouvre deux fenêtres (backend et frontend).
Ouvrez ensuite http://localhost:5173 dans le navigateur.
Pour arrêter : fermez les deux fenêtres (ou Ctrl+C dedans).

À la place, vous pouvez double-cliquer séparément sur `START_BACKEND.bat` et `START_FRONTEND.bat`.
Ces scripts installent eux-mêmes ce qui manque au premier lancement (environnement Python, dépendances).

## Installation initiale

### Étape 1 — Installer Python et Node.js (une seule fois)

Vérifiez d'abord s'ils sont déjà installés :

```powershell
python --version
node --version
```

Si une commande n'est pas reconnue, installez-la :

```powershell
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
```

Fermez puis rouvrez PowerShell, et refaites les deux commandes `--version`.

### Étape 2 — Se placer dans le projet

```powershell
cd "C:\Users\WINDOWS 11\OneDrive\Desktop\MZ-SITEHUB-COMPLET\MZ-SITEHUB"
```

### Étape 3 — Créer l'environnement Python et installer les dépendances

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell refuse l'activation (« l'exécution de scripts est désactivée »), tapez une fois :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

puis relancez `.\venv\Scripts\Activate.ps1`.
(Les fichiers `START_*.bat` n'ont pas besoin de cette commande.)

### Étape 4 — Installer les dépendances du frontend

```powershell
cd ..\frontend
npm install
```

Si npm affiche une erreur `ERESOLVE`, utilisez : `npm install --legacy-peer-deps`.
Les messages « vulnerabilities » ne sont pas bloquants. N'utilisez pas `npm audit fix --force`.

### Étape 5 — Configurer le fichier .env (le backend ne démarre pas sans lui)

```powershell
cd ..
Copy-Item .env.example backend\.env
notepad backend\.env
```

Dans le Bloc-notes, remplissez :

- `DATABASE_URL` : adresse de la base (Supabase : bouton **Connect**, « Transaction pooler »).
  Elle doit commencer par `postgresql+asyncpg://`.
- `JWT_SECRET` : générez une valeur aléatoire avec cette commande et collez le résultat :

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Le fichier `backend\.env` contient des secrets : ne l'envoyez à personne et ne le publiez jamais.

### Étape 6 — Initialiser la base de données

Si vous utilisez la base Supabase déjà en place, **ne faites rien** : les tables existent déjà.
Pour une base neuve et vide, les scripts SQL sont dans le dossier `database\migrations\`
(à exécuter dans l'ordre, par exemple avec l'éditeur SQL de Supabase).

### Étape 7 — Créer le premier compte administrateur

Uniquement si aucun compte n'existe encore (le script ne modifie jamais un compte existant) :

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m scripts.seed_admin --email admin@mzbuilding.dz --password "VotreMotDePasseSolide"
```

Pour changer le mot de passe d'un compte déjà existant (le mot de passe est demandé à l'écran) :

```powershell
python -m scripts.reset_admin_password
```

### Étape 8 — Démarrer

Utilisez `START_TOUT.bat` (voir plus haut), ou à la main dans **deux fenêtres PowerShell** :

Fenêtre 1 (backend) :

```powershell
cd "C:\Users\WINDOWS 11\OneDrive\Desktop\MZ-SITEHUB-COMPLET\MZ-SITEHUB\backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Fenêtre 2 (frontend) :

```powershell
cd "C:\Users\WINDOWS 11\OneDrive\Desktop\MZ-SITEHUB-COMPLET\MZ-SITEHUB\frontend"
npm run dev
```

- Interface : http://localhost:5173
- Documentation de l'API : http://localhost:8000/docs

## Tests automatiques du backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest
```

## Problèmes courants

**« Le port 8000 est déjà utilisé »** : un ancien backend tourne encore. Fermez son ancienne fenêtre, ou :

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Erreur 500 à la connexion, avec `WinError 121` ou `timed out` dans la fenêtre du backend** : le PC n'arrive
pas à joindre la base. Testez le réseau (remplacez l'adresse par celle de votre `DATABASE_URL`) :

```powershell
Test-NetConnection VOTRE_HOTE.pooler.supabase.com -Port 6543
```

Si `TcpTestSucceeded` vaut `False`, essayez un autre réseau (par exemple le partage de connexion du téléphone)
et vérifiez que le projet Supabase n'est pas en pause.

**« Email ou mot de passe incorrect » alors que le mot de passe est bon** : regardez la fenêtre du backend.
Un code `401` signifie un mot de passe différent (utilisez `reset_admin_password`) ; un code `500` signifie un
problème de base de données.

**Wilayas et communes vides** : normal pour l'instant, elles seront ajoutées plus tard depuis l'administration.
Les formulaires fonctionnent sans elles.
