-- Modifying Data

-- Insert
INSERT INTO cd.facilities
  (facid, name, membercost, guestcost, initialoutlay, monthlymaintenance)
VALUES
  (9, 'Spa', 20, 30, 100000, 800);

-- Insert from Select
INSERT INTO cd.facilities
  (facid, name, membercost, guestcost, initialoutlay, monthlymaintenance)
SELECT
  (SELECT MAX(facid) FROM cd.facilities) + 1,
  'Spa', 20, 30, 100000, 800;

-- Update
UPDATE cd.facilities
SET initialoutlay = 10000
WHERE facid = 1;

-- Update with Calculation
UPDATE cd.facilities
SET
  membercost = membercost * 1.1,
  guestcost  = guestcost  * 1.1
WHERE facid IN (0, 1);

-- Delete All
DELETE FROM cd.bookings;

-- Delete with Condition
DELETE FROM cd.members
WHERE memid NOT IN (SELECT memid FROM cd.bookings);

-- Basics

-- Where 2
SELECT facid, name, membercost, monthlymaintenance
FROM cd.facilities
WHERE membercost > 0
  AND membercost < (monthlymaintenance / 50.0);

-- Where 3
SELECT *
FROM cd.facilities
WHERE name LIKE '%Tennis%';

-- Where 4
SELECT *
FROM cd.facilities
WHERE facid IN (1, 5);

-- Date
SELECT memid, surname, firstname, joindate
FROM cd.members
WHERE joindate >= '2012-09-01';

-- Union
SELECT surname FROM cd.members
UNION
SELECT name FROM cd.facilities;

-- Joins

-- Simple Join
SELECT
  bks.starttime
FROM cd.bookings bks
INNER JOIN cd.members mems
  ON bks.memid = mems.memid
WHERE mems.firstname = 'David'
  AND mems.surname = 'Farrell';

-- Simple Join 2
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

-- Self Join (Three Joins)
SELECT DISTINCT
  recs.firstname AS recfirstname,
  recs.surname   AS recsurname,
  mems.firstname AS memfirstname,
  mems.surname   AS memsurname
FROM cd.members mems
INNER JOIN cd.members recs
  ON recs.memid = mems.recommendedby
ORDER BY recsurname, recfirstname;

-- Self Join
SELECT DISTINCT
  mems.firstname || ' ' || mems.surname AS member,
  recs.firstname || ' ' || recs.surname AS recommender
FROM cd.members mems
LEFT JOIN cd.members recs
  ON recs.memid = mems.recommendedby
ORDER BY member;

-- Subquery and Join
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

-- Aggregation

-- Count Group By Order By
SELECT
  recommendedby,
  COUNT(*) AS count
FROM cd.members
WHERE recommendedby IS NOT NULL
GROUP BY recommendedby
ORDER BY recommendedby;

-- Facility Hours
SELECT
  facid,
  SUM(slots) AS "Total Slots"
FROM cd.bookings
GROUP BY facid
ORDER BY facid;

-- Facility Hours by Month
SELECT
  facid,
  EXTRACT(MONTH FROM starttime) AS month,
  SUM(slots) AS "Total Slots"
FROM cd.bookings
WHERE EXTRACT(YEAR FROM starttime) = 2012
GROUP BY facid, month
ORDER BY facid, month;

-- Facility Hours by Month Multi Col
SELECT
  facid,
  EXTRACT(MONTH FROM starttime) AS month,
  SUM(slots) AS slots
FROM cd.bookings
WHERE starttime >= '2012-01-01'
  AND starttime < '2013-01-01'
GROUP BY facid, month
ORDER BY facid, month;

-- Count Distinct Members
SELECT COUNT(DISTINCT memid) FROM cd.bookings;

-- Bookings Group By Join
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

-- Count Members Window
SELECT
  COUNT(*) OVER(),
  firstname,
  surname
FROM cd.members
ORDER BY joindate;

-- Num Members Window
SELECT
  ROW_NUMBER() OVER(ORDER BY joindate) AS row_number,
  firstname,
  surname
FROM cd.members
ORDER BY joindate;

-- Facility Hours Window Subquery
SELECT
  facid,
  total
FROM (
  SELECT
    facid,
    SUM(slots) AS total,
    RANK() OVER (ORDER BY SUM(slots) DESC) AS rank
  FROM cd.bookings
  GROUP BY facid
) AS ranked
WHERE rank = 1;

-- String

-- Concat
SELECT
  surname || ', ' || firstname AS name
FROM cd.members;

-- Regex Where
SELECT *
FROM cd.members
WHERE telephone ~ '[()]';

-- Substr Group By
SELECT
  SUBSTR(surname, 1, 1) AS letter,
  COUNT(*) AS count
FROM cd.members
GROUP BY letter
ORDER BY letter;
