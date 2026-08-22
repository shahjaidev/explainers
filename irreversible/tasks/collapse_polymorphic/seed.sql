CREATE TABLE posts (
  id    INTEGER PRIMARY KEY,
  title TEXT NOT NULL
);

INSERT INTO posts (id, title) VALUES
  (101, 'On the Analytical Engine'),
  (102, 'Compilers considered useful'),
  (103, 'Orbital mechanics by hand'),
  (104, 'The halting problem, informally');

CREATE TABLE photos (
  id      INTEGER PRIMARY KEY,
  caption TEXT NOT NULL
);

-- Photo ids are drawn from a disjoint range, so a bare id is unambiguous.
INSERT INTO photos (id, caption) VALUES
  (201, 'Mark I, front panel'),
  (202, 'Whirlwind core memory'),
  (203, 'ENIAC patch panel');

CREATE TABLE comments (
  id          INTEGER PRIMARY KEY,
  body        TEXT NOT NULL,
  parent_type TEXT NOT NULL,
  parent_id   INTEGER NOT NULL
);

INSERT INTO comments (id, body, parent_type, parent_id) VALUES
  (1, 'The loop notation here is decades ahead of its time', 'post',  101),
  (2, 'Bookmarking this for the reading group',             'post',  101),
  (3, 'Does this still hold for self-hosting compilers',    'post',  102),
  (4, 'The slide rule work is the impressive part',         'post',  103),
  (5, 'Second half lost me but the setup is clear',         'post',  104),
  (6, 'You can read the switch labels in the full size',    'photo', 201),
  (7, 'Those cores were threaded by hand',                  'photo', 202),
  (8, 'Every one of those cables was a program',            'photo', 203);
