CREATE TABLE users (
  id    INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  name  TEXT NOT NULL
);

-- ids 3, 5, 7 and 9 are duplicate signups of 1, 2, 1 and 4.
INSERT INTO users (id, email, name) VALUES
  (1, 'ada@analytical.example',     'Ada Lovelace'),
  (2, 'grace@compiler.example',     'Grace Hopper'),
  (3, 'ada@analytical.example',     'A. Lovelace'),
  (4, 'katherine@orbital.example',  'Katherine Johnson'),
  (5, 'grace@compiler.example',     'G. Hopper'),
  (6, 'alan@decidable.example',     'Alan Turing'),
  (7, 'ada@analytical.example',     'Ada L.'),
  (8, 'barbara@abstraction.example','Barbara Liskov'),
  (9, 'katherine@orbital.example',  'K. Johnson'),
  (10, 'radia@spanning.example',    'Radia Perlman');

CREATE TABLE orders (
  id      INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  total   REAL NOT NULL
);

-- Four of the ten orders point at a duplicate row, so deleting duplicates
-- before repointing loses exactly those four.
INSERT INTO orders (id, user_id, total) VALUES
  (1,  1, 42.50),
  (2,  3,  9.99),
  (3,  2, 120.00),
  (4,  5, 15.25),
  (5,  4, 88.10),
  (6,  7, 31.00),
  (7,  6, 12.75),
  (8,  9, 64.40),
  (9,  8,  5.05),
  (10, 10, 77.30);
