from flask import Flask, jsonify, request, render_template
from neo4j import GraphDatabase, basic_auth

URI  = "neo4j+s://96eeb76b.databases.neo4j.io"
USER = "neo4j"
PWD  = "password_here"

app = Flask(__name__)

driver = GraphDatabase.driver(
    URI,
    auth=basic_auth(USER, PWD),
    connection_timeout=15,        
    max_connection_lifetime=60*60 
)

def get_course_recommendations(tx, major):
    query = """
    MATCH (m:Major {name: $major})-[r:HAS_COURSE]->(c:Course)
    OPTIONAL MATCH (c)-[b:BUNDLED_WITH {major: $major}]-(other:Course)
    OPTIONAL MATCH (c)<-[took:TOOK]-(s:Student)-[:HAS_MAJOR]->(m)
    WITH c, r.popularity AS popularity, 
         COALESCE(SUM(b.count), 0) AS bundle_score,
         COLLECT(took.grade) AS grades
    WITH c, popularity, bundle_score,
         [grade in grades WHERE grade IS NOT NULL | toFloat(grade)] AS numeric_grades
    RETURN c.code AS code, 
           c.name AS name, 
           (bundle_score * 0.7 + popularity * 0.3) AS score,
           CASE WHEN size(numeric_grades) > 0 
                THEN round(
                    reduce(total = 0.0, n IN numeric_grades | total + n)
                    / size(numeric_grades),
                    2)
                ELSE NULL END AS avg_grade
    ORDER BY score DESC
    LIMIT 10
    """
    result = tx.run(query, major=major)
    return [dict(record) for record in result]

#Pages in the site
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add')
def add_form():
    return render_template('add.html')

#Get recommendation endpoint
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

#Post new student data endpoint
@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.get_json()
    
    student_id = data.get('student_id')
    major = data.get('major')
    grad_year = data.get('grad_year')
    courses = data.get('courses', [])

    if not all([student_id, major, grad_year]) or not courses:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        with driver.session() as session:
            # Create student and link to major
            session.write_transaction(
                lambda tx: tx.run(
                    """
                    MERGE (s:Student {id: $student_id})
                    SET s.major = $major, s.grad_year = $grad_year
                    WITH s
                    MERGE (m:Major {name: $major})
                    MERGE (s)-[:HAS_MAJOR]->(m)
                    """,
                    student_id=student_id, major=major, grad_year=grad_year
                )
            )

            # Add courses and relationships
            for course in courses:
                session.write_transaction(
                    lambda tx: tx.run(
                        """
                        MATCH (s:Student {id: $student_id})
                        MERGE (c:Course {code: $course_id})
                        MERGE (s)-[t:TOOK]->(c)
                        SET t.grade = $grade, t.level = $level
                        """,
                        student_id=student_id,
                        course_id=course['course_id'],
                        grade=course['grade'],
                        level=course['level']
                    )
                )

            # Update score
            session.write_transaction(
                lambda tx: tx.run(
                    """
                    MATCH (m:Major {name: $major})
                    MATCH (c:Course)<-[:TOOK]-(s:Student)-[:HAS_MAJOR]->(m)
                    WITH m, c, COUNT(s) AS new_popularity
                    MERGE (m)-[r:HAS_COURSE]->(c)
                    SET r.popularity = new_popularity
                    """,
                    major=major
                )
            )

            return jsonify({"success": True}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Load existing courses and majors in the db to site
@app.route('/api/courses', methods=['GET'])
def get_all_courses():
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (c:Course) RETURN c.code AS code, c.name AS name"
            )
            courses = [dict(record) for record in result]
            return jsonify(courses)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/majors', methods=['GET'])
def get_all_majors():
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (m:Major) RETURN DISTINCT m.name AS name"
            )
            majors = [dict(record) for record in result]
            return jsonify(majors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)