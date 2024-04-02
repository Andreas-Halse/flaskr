drop table if exists entries;
create table entries (
  id integer primary key autoincrement,
  title text not null,
  'text' text not null,
  created_at TEXT DEFAULT (datetime('now'))
);