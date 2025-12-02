# Budgetia — V1 (Next.js) — Projet prêt à déployer sur Vercel


Ce fichier contient :


1. Un **README** avec instructions d'installation et déploiement
2. Un **scaffold complet** (fichiers clés) pour une application Next.js (App Router) responsive mobile+PC
3. Composants React réutilisables (BudgetCard, ExpenseForm, ChartStub)
4. Stockage local via **localStorage** (pour V1) — aucune base externe requise (idéal pour tester et déployer sur Vercel Hobby)
5. Fonction d'export (CSV / XLSX / PDF) via bibliothèques JS (indications d'installation)
6. Logique d'alertes (70/90/100%) et visuels
7. Styles Tailwind + mode sombre


---


## README (extrait - Instructions rapides)


### Prérequis
- Node 18+ (ou version recommandée par Vercel)
- Git


### Installer
```bash
git clone <votre-repo>
cd budgetia-v1
npm install
npm run dev
```
Lancer l'app en local : http://localhost:3000


### Déployer sur Vercel
1. Crée un repo GitHub/GitLab/Bitbucket et push le projet
2. Sur vercel.com -> New Project -> Importer depuis ton repo
3. Variables d'environnement : AUCUNE requise pour la V1 locale (localStorage). Pour Supabase/Firebase plus tard -> ajouter
4. Déployer. Vercel détecte Next.js automatiquement.


---