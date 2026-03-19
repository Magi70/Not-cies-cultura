# Diari de Cultura 🗞️

Pàgina web que s'actualitza automàticament cada dia a les 7h amb les notícies culturals de Catalunya, Espanya i Europa.

## Com funciona

Un GitHub Action s'executa cada matí, crida l'API de Claude amb cerca web, genera el `index.html` estàtic amb les notícies incrustades i el publica via GitHub Pages. Tu obres la URL i les notícies ja estan.

## Configuració pas a pas

### 1. Crea el repositori a GitHub
- Crea un repositori nou, per exemple `diari-cultura`
- Puja tots aquests fitxers (manté l'estructura de carpetes)

### 2. Obtén una API key d'Anthropic
- Ve a [console.anthropic.com](https://console.anthropic.com)
- Registra't o inicia sessió
- Ves a *API Keys* → *Create Key*
- Afegeix crèdits (mínim $5, duren mesos a aquest ritme d'ús)

### 3. Afegeix la API key com a Secret a GitHub
- Al teu repositori: **Settings → Secrets and variables → Actions**
- Clica **New repository secret**
- Nom: `ANTHROPIC_API_KEY`
- Valor: la teva API key (`sk-ant-...`)

### 4. Activa GitHub Pages
- Al teu repositori: **Settings → Pages**
- Source: **GitHub Actions** (no "Deploy from branch")

### 5. Executa el primer cop manualment
- Ves a la pestanya **Actions** del teu repositori
- Clica el workflow **"Actualitzar Notícies de Cultura"**
- Clica **"Run workflow"**
- Espera ~2 minuts

### 6. Accedeix a la teva pàgina
La URL serà: `https://TU_USUARI.github.io/diari-cultura`

## Estructura de fitxers

```
diari-cultura/
├── index.html                          ← Pàgina generada automàticament
├── generate.py                         ← Script que crida Claude i genera el HTML
├── README.md                           ← Aquest fitxer
└── .github/
    └── workflows/
        └── update-news.yml             ← GitHub Action (s'executa a les 7h)
```

## Coste estimat

- ~$0.03–0.05 per execució
- ~$1–1.5 al mes

## Executar localment (opcional)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python generate.py
```
