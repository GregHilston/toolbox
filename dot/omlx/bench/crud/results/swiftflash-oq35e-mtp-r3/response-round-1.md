

The root cause: I never added `express.json()` middleware, so POST/PUT bodies arrived as `undefined`. Every POST returned 400 (breaking create) and every PUT returned 404 (breaking update, and making the validation-PUT check return 404). The UI tests then had no books to render, so the toggle/edit/delete clicks failed. Adding JSON body parsing fixes all of it.

### server/index.js
```js
const express = require("express");
const Database = require("better-sqlite3");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

// Parse JSON request bodies (fixes create/update/validation)
app.use(express.json());

const db = new Database(path.join(__dirname, "data.db"));

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER DEFAULT 0
  )
`);

// ---------- GET all books ----------
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(rows.map(mapRow));
});

// ---------- GET one book ----------
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(mapRow(row));
});

// ---------- CREATE ----------
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body || {};

  if (!title || !author) {
    return res.status(400).json({ error: "title and author are required" });
  }

  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json(mapRow(row));
});

// ---------- UPDATE ----------
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body || {};

  if (!title || !author) {
    return res.status(400).json({ error: "title and author are required" });
  }

  db.prepare("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?").run(
    title.trim(),
    author.trim(),
    year ?? null,
    read ? 1 : 0,
    id
  );

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json(mapRow(row));
});

// ---------- DELETE ----------
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ ok: true });
});

// ---------- helpers ----------
function mapRow(row) {
  return { ...row, read: Boolean(row.read) };
}

app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```