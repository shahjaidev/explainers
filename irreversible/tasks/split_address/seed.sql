CREATE TABLE users (
  id      INTEGER PRIMARY KEY,
  name    TEXT NOT NULL,
  address TEXT NOT NULL
);

INSERT INTO users (id, name, address) VALUES
  (1,  'Ada Lovelace',      '12 Wilton Crescent, London'),
  (2,  'Grace Hopper',      '440 Elm Street, Arlington'),
  (3,  'Katherine Johnson', '89 Sycamore Lane, Hampton'),
  (4,  'Alan Turing',       '7 Adlington Road, Wilmslow'),
  (5,  'Barbara Liskov',    '221 Vassar Street, Cambridge'),
  (6,  'Edsger Dijkstra',   '3 Plataanstraat, Nuenen'),
  (7,  'Frances Allen',     '55 Peru Road, Peru NY'),
  (8,  'Tony Hoare',        '18 Keble Road, Oxford'),
  (9,  'Radia Perlman',     '900 Chelmsford Street, Lowell'),
  (10, 'Leslie Lamport',    '64 Hillside Avenue, Mount Vernon'),
  (11, 'Jean Bartik',       '5 Gentry Street, Alanthus Grove'),
  (12, 'Margaret Hamilton', '41 Draper Court, Cambridge');

CREATE TABLE orders (
  id      INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  total   REAL NOT NULL
);

INSERT INTO orders (id, user_id, total) VALUES
  (1, 1, 42.50), (2, 1, 9.99), (3, 3, 120.00), (4, 7, 15.25), (5, 12, 88.10);
