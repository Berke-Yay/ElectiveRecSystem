from flask import Flask, jsonify, request, render_template
from neo4j import GraphDatabase

app = Flask(__name__)

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "postgresql!") 
)

def get_course_recommendations(tx, major):
    query = """
    MATCH (m:Major {name: $major})-[r:HAS_COURSE]->(c:Course)
    OPTIONAL MATCH (c)-[b:BUNDLED_WITH {major: $major}]-(other:Course)
    WITH c, r.popularity AS popularity, COALESCE(SUM(b.count), 0) AS bundle_score
    RETURN c.code AS code, 
           c.name AS name, 
           (bundle_score * 0.7 + popularity * 0.3) AS score
    ORDER BY score DESC
    LIMIT 10
    """
    result = tx.run(query, major=major)
    return [dict(record) for record in result]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['GET'])
def recommend():
    major = request.args.get('major', '').strip().title()
    if not major:
        return jsonify({"error": "Major parameter is required"}), 400
    
    try:
        with driver.session() as session:
            recommendations = session.execute_read(
                get_course_recommendations,
                major
            )
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)