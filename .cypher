LOAD CSV WITH HEADERS FROM 'http://localhost:11001/project-91bbe585-5892-49fc-8941-c8c87f241c44/students.csv' AS row
MERGE (s:Student {id: row.student_id})
SET s.major = row.major, s.grad_year = row.grad_year;

LOAD CSV WITH HEADERS FROM 'http://localhost:11001/project-91bbe585-5892-49fc-8941-c8c87f241c44/courses.csv' AS row
MERGE (c:Course {code: row.course_id})
SET c.name = row.course_name;

LOAD CSV WITH HEADERS FROM 'http://localhost:11001/project-91bbe585-5892-49fc-8941-c8c87f241c44/enrollments.csv' AS row
MERGE (s:Student {id: row.student_id})
MERGE (c:Course {code: row.course_id})
MERGE (s)-[t:TOOK]->(c)
SET t.grade = row.grade, t.level = row.level;

MATCH (s:Student)
MERGE (m:Major {name: s.major})
MERGE (s)-[:HAS_MAJOR]->(m);

MATCH (m:Major)
WITH m
MATCH (c:Course)<-[:TOOK]-(s:Student)-[:HAS_MAJOR]->(m)
WITH m, c, COUNT(s) AS popularity
MERGE (m)-[r:HAS_COURSE]->(c)
SET r.popularity = popularity;

MATCH (s:Student)-[:HAS_MAJOR]->(m:Major)
WITH m, s
MATCH (s)-[:TOOK]->(c1:Course)
WITH m, COLLECT(c1) AS courses
UNWIND courses AS c1
UNWIND courses AS c2
WITH m, c1, c2
WHERE c1.code < c2.code
MERGE (c1)-[b:BUNDLED_WITH {major: m.name}]->(c2)
ON CREATE SET b.count = 1
ON MATCH SET b.count = b.count + 1;