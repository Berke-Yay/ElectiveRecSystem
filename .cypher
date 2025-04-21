LOAD CSV WITH HEADERS FROM 'http://localhost:11001/project-91bbe585-5892-49fc-8941-c8c87f241c44/courses.csv' AS row
MERGE (c:Course {code: row.course_id})
SET c.name = row.course_name;