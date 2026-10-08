# Trivial Pursuit — Entre Potes (version mobile / PWA)

Application web installable : elle tourne dans le navigateur du téléphone, se « installe » sur l'écran
d'accueil et fonctionne **hors ligne**. Aucun serveur n'est nécessaire une fois l'application chargée.

## Tester sur le PC

```
cd pwa
python -m http.server 8000
```

Puis ouvrir <http://localhost:8000> (idéalement en mode « appareil mobile » des outils de développement).

## Mettre l'application sur le téléphone

Le mode « installable » et le hors-ligne exigent **HTTPS**. Le plus simple est d'héberger le dossier `pwa/`
sur un service gratuit de sites statiques :

- **Netlify** (le plus simple) : aller sur <https://app.netlify.com/drop> et glisser-déposer le dossier `pwa/`.
  Sans compte, le site disparaît au bout d'environ une heure : créer un compte gratuit et « claim » le site.
- **Cloudflare Pages** : même principe (envoi direct du dossier `pwa/`).
- **GitHub Pages** : il ne publie que la racine du dépôt ou un dossier `docs/` (pas `pwa/`). Renommer `pwa` en
  `docs`, pousser le dépôt, puis *Settings → Pages* → branche `main`, dossier `/docs`.

Ensuite, sur le téléphone, ouvrir l'adresse obtenue :

- **Android (Chrome)** : menu ⋮ → *Installer l'application* (ou le bouton « Installer » du menu du jeu).
- **iPhone (Safari)** : bouton Partager → *Sur l'écran d'accueil*.

Une fois ouverte une première fois avec du réseau, l'application est mise en cache et marche sans connexion.

## Transférer les questions (PC ⇄ téléphone)

Les questions sont stockées **sur chaque appareil** (stockage du navigateur). Pour les copier :

1. Sur l'appareil source : *Questions → Exporter Excel* (sur le PC : *Questions → Exporter vers Excel…*).
2. Envoyer le fichier `.xlsx` vers l'autre appareil (mail, cloud, câble, bouton « Partager… » du téléphone).
3. Sur l'appareil cible : *Questions → Importer Excel* (une feuille = un thème).

L'import ignore les questions déjà présentes : on peut réimporter un fichier sans créer de doublons.
Le fichier exporté sert aussi de **sauvegarde** : le navigateur peut vider ses données (nettoyage, iPhone
inutilisé pendant plusieurs semaines…).

## Mettre à jour l'application

Après toute modification d'un fichier, augmenter `CACHE_VERSION` dans `sw.js` (ex. `tp-v4` → `tp-v5`) avant de
republier, sinon les téléphones gardent l'ancienne version en cache.

## Contenu

| Fichier | Rôle |
|---|---|
| `index.html`, `style.css` | Page et styles |
| `js/app.js` | Écrans (menu, assistant, partie, questions, paramètres) |
| `js/engine.js` | Règles du jeu (équivalent de `app/game_engine.py`) |
| `js/store.js` | Thèmes, questions, réglages et partie sauvegardée |
| `js/wheel.js`, `js/sound.js` | Roue animée et sons générés |
| `js/excel.js` + `lib/xlsx.full.min.js` | Import / export Excel (SheetJS) |
| `sw.js`, `manifest.webmanifest`, `icons/` | Mode hors ligne et installation |
