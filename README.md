# MaxBoard

Application locale de whiteboard enseignant, synchronisee en direct sur le meme Wi-Fi.

## Fonctionnalites

- Gestion de cours (creer, renommer, dupliquer, supprimer, reordonner)
- Plusieurs whiteboards par cours (creer, renommer, dupliquer, supprimer, reordonner)
- Copie d'un whiteboard vers un autre cours (avec hotspots)
- Whiteboard temps reel (stylo, aquarelle, gomme, clear, undo, zoom, pan)
- Coller des images depuis le presse-papiers
- Hotspots (ajout, edition, suppression) avec contenu HTML leger
- Mode consultation etudiant (lecture + ouverture hotspots)
- QR et URL separes: etudiants et prof distant
- Chat hotspot avec LLM local (Qwen), file d'attente globale (5), timeout auto, supervision prof
- RAG local combine: hotspot courant + tous hotspots + PDFs du cours
- Gestion PDFs par cours (ajout, renommer, supprimer) avec reindexation auto immediate
- Export PNG
- Export PDF: image du whiteboard + hotspots tries alphabetiquement (titre + contenu)
- Export/import de whiteboard (.maxboard.json) pour echange entre profs
- Sauvegarde automatique en temps reel dans `data/state.json`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
python server.py
```

Puis ouvrir:

- `http://localhost:8080` (poste principal prof)
- QR etudiant: `/?mode=student`
- QR prof distant: `/?mode=teacher&remote=1`

## IA locale

- Modele par defaut: `/Users/stt/GIT/models/qwen2.5-3b-instruct-q4_k_m.gguf`
- Override possible avec `MAXBOARD_MODEL_PATH`
- Embeddings RAG: `BAAI/bge-small-en-v1.5` (fastembed)

## IA Apertus (Infomaniak)

Provider selectable via env:

- `MAXBOARD_LLM_PROVIDER=local|apertus` (defaut `local`)
- `MAXBOARD_APERTUS_MODEL` (defaut `meta-llama/Llama-3.3-70B-Instruct`)
- Option 1 (URL explicite): `MAXBOARD_APERTUS_API_URL` + `MAXBOARD_INFOMANIAK_API_TOKEN`
- Option 2 (derivee Infomaniak): `MAXBOARD_INFOMANIAK_PRODUCT_ID` + `MAXBOARD_INFOMANIAK_API_TOKEN`

Exemple:

```bash
export MAXBOARD_LLM_PROVIDER=apertus
export MAXBOARD_INFOMANIAK_PRODUCT_ID=XXXXX
export MAXBOARD_INFOMANIAK_API_TOKEN=sk-xxxxx
python server.py
```
