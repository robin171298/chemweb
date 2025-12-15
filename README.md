# ChemDB Nervous System Drugs — Web App

Flask + MySQL web app for exploring nervous-system drugs. Includes HTML UI, JSON API, charts, and detail views with structure images and synonyms.

## Components
- **Backend:** `app.py` (Flask, mysql-connector). Routes for HTML pages (`/`, `/drugs`, `/drug/<cid>`, About/Help/Contact) and JSON API (`/api/drugs`, `/api/drug/<cid>`).
- **Database:** MySQL `chemdb` with `nervous_system_drugs` table (all compound fields) and `synonyms` table (id, inchikey, source, synonym).
- **Frontend:** Jinja templates in `Templates/`, styling in `static/style.css`. Charts and filters on the main page; search results page shows lists and bar charts; detail page shows structure, properties, Lipinski summary, and synonyms toggle.

## Running
1. Ensure MySQL `chemdb` is available and accessible by the credentials in `app.py` (`DB_CONFIG`).
2. Create/activate the conda env from `environment.yml`:  
   ```bash
   conda env create -f environment.yml
   conda activate chemweb
   ```
3. From `chemweb/`, start the app:  
   ```bash
   python app.py
   ```  
   (or `flask run` if configured).
4. Open `http://127.0.0.1:5000/`.

## Key Routes (HTML)
- `/` — overview, class counts, top 10 literature/patents, Lipinski charts, other parameter charts, intro text.
- `/drugs` — search/filter (by `?class=` or `?q=`), table of results, top-10 literature/patent bars.
- `/drug/<Compound_CID>` — detail page with structure image, properties, Lipinski table/pie, synonyms toggle (from `synonyms` table).
- `/help`, `/about`, `/contact` — static info pages.

## JSON API
- `/api/drugs` — optional `class`, `limit` (default 100), `offset` (default 0). Returns `{count, results}` with all columns.
  - Example: `/api/drugs?limit=500`
  - Example: `/api/drugs?class=benzodiazepine&limit=50&offset=0`
- `/api/drug/<cid>` — single record by `Compound_CID`; 404 with `{"error": "Drug not found"}` if missing.

## Data Notes
- `nervous_system_drugs` columns include identification (CID, Name, InChIKey, SMILES, IUPAC), physchem (MW, formula, XLogP, Polar_Area, H-bond donor/acceptor, rotatable bonds, complexity, stereocounts), literature/patent counts, mechanism, medical use, and `drug_class`.
- `synonyms` lookup by `inchikey` feeds the synonyms table on the drug detail page.

## UI Highlights
- Search bar with example chips (Penfluridol, Mephobarbital).
- Charts (histograms, pie) driven by inline JS in `Templates/index.html`; styles in `static/style.css`.
- Detail page fetches PubChem PNG by CID and shows Lipinski pass/fail with pie chart.
