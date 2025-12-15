from flask import Flask, render_template, request, jsonify
import mysql.connector


app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Labor.2024",
    "database": "chemdb",
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/")
def index():
    """
    Show drug classes with counts.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT drug_class, COUNT(*) AS count
        FROM nervous_system_drugs
        GROUP BY drug_class
        ORDER BY drug_class;
    """)
    classes = cursor.fetchall()

    cursor.execute("""
        SELECT Name, Compound_CID, Linked_PubChem_Literature_count AS literature_count
        FROM nervous_system_drugs
        WHERE Linked_PubChem_Literature_count IS NOT NULL
        ORDER BY Linked_PubChem_Literature_count DESC
        LIMIT 10;
    """)
    top_literature = cursor.fetchall()

    cursor.execute("""
        SELECT Name, Compound_CID, Linked_PubChem_Patent_Count AS patent_count
        FROM nervous_system_drugs
        WHERE Linked_PubChem_Patent_Count IS NOT NULL
        ORDER BY Linked_PubChem_Patent_Count DESC
        LIMIT 10;
    """)
    top_patents = cursor.fetchall()

    cursor.execute("""
        SELECT Name, drug_class, Molecular_Weight, XLogP,
               Polar_Area, Rotatable_Bond_Count, Complexity, Total_Atom_Stereo_Count, Charge,
               `H-Bond_Donor_Count` AS h_bond_donor_count,
               `H-Bond_Acceptor_Count` AS h_bond_acceptor_count
        FROM nervous_system_drugs;
    """)
    lipinski_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        classes=classes,
        top_literature=top_literature,
        top_patents=top_patents,
        lipinski_data=lipinski_data,
        search_query="",
    )


@app.route("/drugs")
def drugs():
    """
    Show drugs, optionally filtered by class.
    /drugs?class=benzodiazepine
    /drugs?q=gaba
    """
    drug_class = request.args.get("class")
    search_query = (request.args.get("q") or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT Name, Compound_CID, Molecular_Formula, Molecular_Weight,
               XLogP, Polar_Area, Mechanism_of_Action, Main_Medical_Use,
               Linked_PubChem_Literature_Count, Linked_PubChem_Patent_Count,
               drug_class
        FROM nervous_system_drugs
    """

    conditions = []
    params = []

    if drug_class:
        conditions.append("drug_class = %s")
        params.append(drug_class)

    if search_query:
        like_term = f"%{search_query}%"
        text_fields = [
            "Name",
            "Molecular_Formula",
            "Mechanism_of_Action",
            "Main_Medical_Use",
            "drug_class",
        ]
        # Search across multiple text columns with OR.
        conditions.append("(" + " OR ".join(f"{col} LIKE %s" for col in text_fields) + ")")
        params.extend([like_term] * len(text_fields))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        {base_query}
        {where_clause}
        ORDER BY drug_class, Name
        LIMIT 200;
    """

    cursor.execute(query, params)

    drugs = cursor.fetchall()

    cursor.close()
    conn.close()

    # Compute top 10 literature/patent counts within current result set
    lit_sorted = sorted(
        (d for d in drugs if d.get("Linked_PubChem_Literature_Count") is not None),
        key=lambda x: x.get("Linked_PubChem_Literature_Count", 0),
        reverse=True,
    )[:10]
    patent_sorted = sorted(
        (d for d in drugs if d.get("Linked_PubChem_Patent_Count") is not None),
        key=lambda x: x.get("Linked_PubChem_Patent_Count", 0),
        reverse=True,
    )[:10]

    return render_template(
        "drugs.html",
        drugs=drugs,
        selected_class=drug_class,
        search_query=search_query,
        top_literature=lit_sorted,
        top_patents=patent_sorted,
    )


@app.route("/drug/<int:compound_cid>")
def drug_detail(compound_cid):
    """
    Show a single drug by Compound_CID.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT Name, Compound_CID, Molecular_Formula, Molecular_Weight,
               XLogP, Polar_Area, Mechanism_of_Action, Main_Medical_Use,
               IUPAC_Name, InChIKey, drug_class,
               `H-Bond_Donor_Count` AS h_bond_donor_count,
               `H-Bond_Acceptor_Count` AS h_bond_acceptor_count
        FROM nervous_system_drugs
        WHERE Compound_CID = %s
        LIMIT 1;
    """,
        (compound_cid,),
    )
    drug = cursor.fetchone()

    synonyms = []
    if drug and drug.get("InChIKey"):
        cursor.execute(
            """
            SELECT synonym, source
            FROM synonyms
            WHERE inchikey = %s
            ORDER BY source, synonym;
            """,
            (drug["InChIKey"],),
        )
        synonyms = cursor.fetchall()

    cursor.close()
    conn.close()

    if not drug:
        return render_template("drug_detail.html", drug=None, search_query=""), 404

    return render_template(
        "drug_detail.html",
        drug=drug,
        synonyms=synonyms,
        search_query="",
    )

@app.route("/api/drugs")
def api_drugs():
    """
    JSON API: list drugs with optional class filter, limit, offset.
    """
    drug_class = request.args.get("class")
    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    # basic sanitation
    limit = max(0, limit)
    offset = max(0, offset)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = "SELECT * FROM nervous_system_drugs"
    params = []
    if drug_class:
        sql += " WHERE drug_class = %s"
        params.append(drug_class)

    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(sql, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({"count": len(rows), "results": rows})


@app.route("/api/drug/<int:cid>") # registers HTTP endpoint. cid = integer parameter for the function
def api_drug(cid): # handler function (called with the request)
    """
    JSON API: single drug by Compound_CID.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute( # execute SQL query
        "SELECT * FROM nervous_system_drugs WHERE Compound_CID = %s LIMIT 1;", (cid,)
    )
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "Drug not found"}), 404

    return jsonify(row)


@app.route("/help")
def help_page():
    """
    Static help page.
    """
    return render_template("help.html", search_query="")


@app.route("/contact")
def contact_page():
    """
    Static contact page.
    """
    return render_template("contact.html", search_query="")


@app.route("/about")
def about_page():
    """
    Static about page.
    """
    return render_template("about.html", search_query="")


if __name__ == "__main__":
    app.run(debug=True)
