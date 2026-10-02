

The problem is that `better-sqlite3` is a native C++ addon that fails to compile against Node.js 26's V8 headers. The fix is to use Node.js's built-in `node:sqlite` module (stable since Node 22), which requires no native compilation.

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require("express");
const { DatabaseSync } = require("node:sqlite");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

// --- Database setup ---
const db = new DatabaseSync(path.join(__dirname, "data.db"));
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN NOT NULL DEFAULT 0
  )
`);

app.use(express.json());

// --- Validation helper ---
function validate(body) {
  const title = (body.title || "").trim();
  const author = (body.author || "").trim();
  if (!title || !author) return null;
  return { title, author };
}

function rowToBook(row) {
  if (!row) return null;
  return { ...row, read: !!row.read };
}

// --- GET /api/books ---
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT id, title, author, year, read FROM books ORDER BY id").all();
  res.json(rows.map(rowToBook));
});

// --- GET /api/books/:id ---
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(rowToBook(row));
});

// --- POST /api/books ---
app.post("/api/books", (req, res) => {
  const valid = validate(req.body);
  if (!valid) return res.status(400).json({ error: "title and author are required" });

  const year = req.body.year !== undefined && req.body.year !== null && req.body.year !== ""
    ? parseInt(req.body.year, 10)
    : null;
  const read = !!req.body.read;

  const info = db.prepare(
    "INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)"
  ).run(valid.title, valid.author, year, read);

  const id = Number(info.lastInsertRowid);
  const created = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(id);
  res.status(201).json(rowToBook(created));
});

// --- PUT /api/books/:id ---
app.put("/api/books/:id", (req, res) => {
  const existing = db.prepare("SELECT id FROM books WHERE id = ?").get(req.params.id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const valid = validate(req.body);
  if (!valid) return res.status(400).json({ error: "title and author are required" });

  const year = req.body.year !== undefined && req.body.year !== null && req.body.year !== ""
    ? parseInt(req.body.year, 10)
    : null;
  const read = !!req.body.read;

  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?"
  ).run(valid.title, valid.author, year, read, req.params.id);

  const updated = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(req.params.id);
  res.json(rowToBook(updated));
});

// --- DELETE /api/books/:id ---
app.delete("/api/books/:id", (req, res) => {
  const info = db.prepare("DELETE FROM books WHERE id = ?").run(req.params.id);
  if (Number(info.changes) === 0) return res.status(404).json({ error: "Book not found" });
  res.status(204).end();
});

app.listen(PORT, () => {
  console.log(`Books API listening on port ${PORT}`);
});
```