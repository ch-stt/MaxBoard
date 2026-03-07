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
