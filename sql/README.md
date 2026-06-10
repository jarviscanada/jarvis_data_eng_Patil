# Introduction

This project demonstrates SQL proficiency through a series of structured query exercises using a PostgreSQL database. The dataset represents a fictional sports club management system containing members, facilities, and booking records. As a developer, I practiced writing queries that cover a wide range of SQL concepts including data manipulation, filtering, joining multiple tables, aggregating results, and working with string functions and window functions.

The intended users of this project are software developers and data engineers looking to strengthen their relational database skills. The technologies used include PostgreSQL for the database engine, Docker for provisioning the database instance, and the psql CLI for executing queries. All queries were written and tested against a locally running PostgreSQL container using the exercises database loaded from the clubdata.sql dataset.

# SQL Queries

###### Table Setup (DDL)

```sql
CREATE TABLE cd.members (
  memid         INTEGER PRIMARY KEY,
  surname       VARCHAR(200) NOT NULL,
  firstname     VARCHAR(200) NOT NULL,
  address       VARCHAR(300) NOT NULL,
  zipcode       INTEGER NOT NULL,
  telephone     VARCHAR(20) NOT NULL,
  recommendedby INTEGER REFERENCES cd.members(memid),
  joindate      TIMESTAMP NOT NULL
);

CREATE TABLE cd.facilities (
  facid              INTEGER PRIMARY KEY,
  name               VARCHAR(100) NOT NULL,
  membercost         NUMERIC NOT NULL,
  guestcost          NUMERIC NOT NULL,
  initialoutlay      NUMERIC NOT NULL,
  monthlymaintenance NUMERIC NOT NULL
);

CREATE TABLE cd.bookings (
  bookid    INTEGER PRIMARY KEY,
  facid     INTEGER REFERENCES cd.facilities(facid),
  memid     INTEGER REFERENCES cd.members(memid),
  starttime TIMESTAMP NOT NULL,
  slots     INTEGER NOT NULL
);
```

---

### Modifying Data

###### Question 1: Insert a new facility

```sql
INSERT INTO cd.facilities
  (facid, name, membercost, guestcost, initialoutlay, monthlymaintenance)
VALUES
  (9, 'Spa', 20, 30, 100000, 800);
```

###### Question 2: Insert from SELECT

```sql
INSERT INTO cd.facilities
  (facid, name, membercost, guestcost, initialoutlay, monthlymaintenance)
SELECT
  (SELECT MAX(facid) FROM cd.facilities) + 1,
  'Spa', 20, 30, 100000, 800;
```

###### Question 3: Update a row

```sql
UPDATE cd.facilities
SET initialoutlay = 10000
WHERE facid = 1;
```

###### Question 4: Update with calculation

```sql
UPDATE cd.facilities
SET
  membercost = membercost * 1.1,
  guestcost  = guestcost  * 1.1
WHERE facid IN (0, 1);
```

###### Question 5: Delete all bookings

```sql
DELETE FROM cd.bookings;
```

###### Question 6: Delete with condition

```sql
DELETE FROM cd.members
WHERE memid NOT IN (SELECT memid FROM cd.bookings);
```

---

### Basics

###### Question 7: WHERE with calculation

```sql
SELECT facid, name, membercost, monthlymaintenance
FROM cd.facilities
WHERE membercost > 0
  AND membercost < (monthlymaintenance / 50.0);
```

###### Question 8: WHERE with LIKE

```sql
SELECT *
FROM cd.facilities
WHERE name LIKE '%Tennis%';
```

###### Question 9: WHERE with IN

```sql
SELECT *
FROM cd.facilities
WHERE facid IN (1, 5);
```

###### Question 10: Filter by date

```sql
SELECT memid, surname, firstname, joindate
FROM cd.members
WHERE joindate >= '2012-09-01';
```

###### Question 11: UNION

```sql
SELECT surname FROM cd.members
UNION
SELECT name FROM cd.facilities;
```

---

### Joins

###### Question 12: Simple JOIN

```sql
SELECT bks.starttime
FROM cd.bookings bks
INNER JOIN cd.members mems
  ON bks.memid = mems.memid
WHERE mems.firstname = 'David'
  AND mems.surname = 'Farrell';
```

###### Question 13: JOIN with filter

```sql
SELECT
  bks.starttime AS start,
  facs.name
FROM cd.bookings bks
INNER JOIN cd.facilities facs
  ON bks.facid = facs.facid
WHERE facs.name IN ('Tennis Court 1', 'Tennis Court 2')
  AND bks.starttime >= '2012-09-21'
  AND bks.starttime < '2012-09-22'
ORDER BY bks.starttime;
```

###### Question 14: Self JOIN  recommenders

```sql
SELECT DISTINCT
  recs.firstname AS recfirstname,
  recs.surname   AS recsurname,
  mems.firstname AS memfirstname,
  mems.surname   AS memsurname
FROM cd.members mems
INNER JOIN cd.members recs
  ON recs.memid = mems.recommendedby
ORDER BY recsurname, recfirstname;
```

###### Question 15: Self JOIN  members with recommenders

```sql
SELECT DISTINCT
  mems.firstname || ' ' || mems.surname AS member,
  recs.firstname || ' ' || recs.surname AS recommender
FROM cd.members mems
LEFT JOIN cd.members recs
  ON recs.memid = mems.recommendedby
ORDER BY member;
```

###### Question 16: Subquery and JOIN

```sql
SELECT DISTINCT
  mems.firstname || ' ' || mems.surname AS member,
  facs.name AS facility
FROM cd.members mems
INNER JOIN cd.bookings bks
  ON bks.memid = mems.memid
INNER JOIN cd.facilities facs
  ON facs.facid = bks.facid
WHERE facs.facid IN (
  SELECT facid FROM cd.facilities WHERE membercost > 0
)
ORDER BY member;
```

---

### Aggregation

###### Question 17: GROUP BY and ORDER BY

```sql
SELECT
  recommendedby,
  COUNT(*) AS count
FROM cd.members
WHERE recommendedby IS NOT NULL
GROUP BY recommendedby
ORDER BY recommendedby;
```

###### Question 18: Total slots per facility

```sql
SELECT
  facid,
  SUM(slots) AS "Total Slots"
FROM cd.bookings
GROUP BY facid
ORDER BY facid;
```

###### Question 19: Total slots per facility per month

```sql
SELECT
  facid,
  EXTRACT(MONTH FROM starttime) AS month,
  SUM(slots) AS "Total Slots"
FROM cd.bookings
WHERE EXTRACT(YEAR FROM starttime) = 2012
GROUP BY facid, month
ORDER BY facid, month;
```

###### Question 20: Total slots per facility per month (multi-column)

```sql
SELECT
  facid,
  EXTRACT(MONTH FROM starttime) AS month,
  SUM(slots) AS slots
FROM cd.bookings
WHERE starttime >= '2012-01-01'
  AND starttime < '2013-01-01'
GROUP BY facid, month
ORDER BY facid, month;
```

###### Question 21: Count distinct members

```sql
SELECT COUNT(DISTINCT memid) FROM cd.bookings;
```

###### Question 22: GROUP BY with JOIN

```sql
SELECT
  mems.surname,
  mems.firstname,
  mems.memid,
  MIN(bks.starttime) AS starttime
FROM cd.bookings bks
INNER JOIN cd.members mems
  ON bks.memid = mems.memid
WHERE bks.starttime >= '2012-09-01'
GROUP BY mems.surname, mems.firstname, mems.memid
ORDER BY mems.memid;
```

###### Question 23: Window function  COUNT OVER

```sql
SELECT
  COUNT(*) OVER(),
  firstname,
  surname
FROM cd.members
ORDER BY joindate;
```

###### Question 24: Window function  ROW_NUMBER

```sql
SELECT
  ROW_NUMBER() OVER(ORDER BY joindate) AS row_number,
  firstname,
  surname
FROM cd.members
ORDER BY joindate;
```

###### Question 25: Window function with subquery

```sql
SELECT facid, total
FROM (
  SELECT
    facid,
    SUM(slots) AS total,
    RANK() OVER (ORDER BY SUM(slots) DESC) AS rank
  FROM cd.bookings
  GROUP BY facid
) AS ranked
WHERE rank = 1;
```

---

### String

###### Question 26: Concatenate strings

```sql
SELECT surname || ', ' || firstname AS name
FROM cd.members;
```

###### Question 27: WHERE with regex

```sql
SELECT *
FROM cd.members
WHERE telephone ~ '[()]';
```

###### Question 28: SUBSTR with GROUP BY

```sql
SELECT
  SUBSTR(surname, 1, 1) AS letter,
  COUNT(*) AS count
FROM cd.members
GROUP BY letter
ORDER BY letter;
```
