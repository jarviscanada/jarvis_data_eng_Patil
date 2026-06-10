# SQL Query Practice

## Table Setup (DDL)

```sql
CREATE TABLE cd.members (
  memid      INTEGER PRIMARY KEY,
  surname    VARCHAR(200) NOT NULL,
  firstname  VARCHAR(200) NOT NULL,
  address    VARCHAR(300) NOT NULL,
  zipcode    INTEGER NOT NULL,
  telephone  VARCHAR(20) NOT NULL,
  recommendedby INTEGER REFERENCES cd.members(memid),
  joindate   TIMESTAMP NOT NULL
);

CREATE TABLE cd.facilities (
  facid        INTEGER PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  membercost   NUMERIC NOT NULL,
  guestcost    NUMERIC NOT NULL,
  initialoutlay    NUMERIC NOT NULL,
  monthlymaintenance NUMERIC NOT NULL
);

CREATE TABLE cd.bookings (
  bookid     INTEGER PRIMARY KEY,
  facid      INTEGER REFERENCES cd.facilities(facid),
  memid      INTEGER REFERENCES cd.members(memid),
  starttime  TIMESTAMP NOT NULL,
  slots      INTEGER NOT NULL
);
```

## Queries

### Modifying Data

#### Insert
```sql

```

#### Insert from Select
```sql

```

#### Update
```sql

```

#### Update with Calculation
```sql

```

#### Delete All
```sql

```

#### Delete with Condition
```sql

```

### Basics

#### Where 2
```sql

```

#### Where 3
```sql

```

#### Where 4
```sql

```

#### Date
```sql

```

#### Union
```sql

```

### Joins

#### Simple Join
```sql

```

#### Simple Join 2
```sql

```

#### Self Join (Three Joins)
```sql

```

#### Self Join
```sql

```

#### Subquery and Join
```sql

```

### Aggregation

#### Count Group By Order By
```sql

```

#### Facility Hours
```sql

```

#### Facility Hours by Month
```sql

```

#### Facility Hours by Month Multi Col
```sql

```

#### Count Distinct Members
```sql

```

#### Bookings Group By Join
```sql

```

#### Count Members Window
```sql

```

#### Num Members Window
```sql

```

#### Facility Hours Window Subquery
```sql

```

### String

#### Concat
```sql

```

#### Regex Where
```sql

```

#### Substr Group By
```sql

```
