# Dal-i — Manual de Proves

Hi ha tres nivells de prova, de més fàcil a més complet.

---

## Nivell 1 — App en viu (sense instal·lar res)

Obre el navegador i accedeix a:

```
https://dal-i-api-y55wqasb6a-ew.a.run.app
```

**Prova bàsica (selecció ràpida):**
1. Prem "Seleccionar imatge" i tria qualsevol foto
2. Fes clic en un dels estils ràpids (Picasso, Van Gogh, Manga…)
3. Prem "Generar Dibuix"
4. ✅ Ha de aparèixer una previsualització SVG i un missatge de confirmació de veu

**Prova multilingüe:**
1. Canvia l'idioma al selector (dalt a la dreta)
2. Escriu un estil en aquell idioma al camp de text (ex: "estilo Van Gogh")
3. Prem "Generar"
4. ✅ La confirmació de veu ha de sonar en l'idioma seleccionat

**Prova de veu:**
1. Prem el botó del micròfon i di "estilo Picasso" (o en l'idioma seleccionat)
2. ✅ Ha de transcriure i processar automàticament

**Prova d'historial:**
1. Genera 2–3 dibuixos
2. Obre el panell lateral "Historial"
3. ✅ Han d'aparèixer els resultats anteriors
4. Prova d'esborrar un element i "Eliminar tot"

---

## Nivell 2 — Tests unitaris locals (sense credencials GCP)

Tots els tests estan completament mockejats. **No cal cap compte de Google.**

### Requisits
- Python 3.12 ([descarregar](https://www.python.org/downloads/))
- Git (per clonar) o descomprimir el ZIP

### Passos

```bash
# 1. Descomprimeix el ZIP i entra a la carpeta
cd Dal-i_Entrega

# 2. Crea un entorn virtual
python3.12 -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Mac / Linux:
source .venv/bin/activate

# 3. Instal·la les dependències
pip install -r backend/requirements.txt

# 4. Executa els tests
cd backend
pytest -v
```

### Resultat esperat

```
tests/test_main.py       ......................   [ OK ]
tests/test_vision.py     ..........             [ OK ]
tests/test_speech.py     ......                 [ OK ]
tests/test_storage.py    ....                   [ OK ]

39 passed in ~5s
```

Si surten **39 passed** (en verd), el codi del backend és correcte.

---

## Nivell 3 — Execució local completa (requereix accés GCP)

> Només necessari si vols provar el servidor localment, no la versió desplegada.
> Necessites ser afegit al projecte GCP (`proyectosm-494910`). Contacta amb Moisés.

### Backend

```bash
# Autenticació
gcloud auth login
gcloud config set project proyectosm-494910
gcloud auth application-default login

# Entorn
cd Dal-i_Entrega
python3.12 -m venv .venv
source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env

# Arrenca
cd backend
uvicorn src.main:app --reload --port 8000
```

Obre `http://localhost:8000/docs` — hauries de veure la documentació interactiva de l'API.

### Frontend

```bash
# En una terminal nova
cd Dal-i_Entrega/frontend
pnpm install    # si no tens pnpm: npm install -g pnpm
pnpm dev
```

Obre `http://localhost:3000`.

---

## Resum ràpid

| Mètode | Temps | Necessita GCP? | Verifica |
|---|---|---|---|
| App en viu | 1 min | No | Tot el sistema end-to-end |
| Tests unitaris | 5 min | No | Lògica del backend |
| Local complet | 15 min | Sí | Integració total en local |

**Per confirmar que funciona n'hi ha prou amb el Nivell 1 + Nivell 2.**
