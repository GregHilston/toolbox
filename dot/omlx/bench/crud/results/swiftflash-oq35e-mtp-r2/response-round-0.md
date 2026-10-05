

### README.md
````markdown
# Books CRUD App

A small full-stack CRUD application managing a `books` table.

## Run the Backend (API)

```bash
cd server
npm install
npm start
# API listens on http://localhost:3001 (override with PORT env var)
```

## Run the Frontend (UI)

```bash
cd client
npm install
npm run dev
# UI served on http://localhost:5173, /api proxied to :3001
```

## Build Frontend for Production

```bash
cd client
npm run build
```
````

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.7.0",
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require("express");
const Database = require("better-sqlite3");
const path = require("path");

const app = express();
const DB_PATH = path.join(__dirname, "data.db");

const db = new Database(DB_PATH);
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

app.use(express.json());

// GET /api/books
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT * FROM books").all();
  res.json(rows.map(row => ({ ...row, read: !!row.read })));
});

// GET /api/books/:id
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json({ ...row, read: !!row.read });
});

// POST /api/books
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body || {};
  if (!title || !title.trim()) return res.status(400).json({ error: "title is required" });
  if (!author || !author.trim()) return res.status(400).json({ error: "author is required" });
  const yearVal = (year !== undefined && year !== null && year !== "") ? parseInt(year, 10) : null;
  const readVal = (read !== undefined) ? (read ? 1 : 0) : 0;
  const info = db.prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)").run(title.trim(), author.trim(), yearVal, readVal);
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json({ ...row, read: !!row.read });
});

// PUT /api/books/:id
app.put("/api/books/:id", (req, res) => {
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(req.params.id);
  if (!existing) return res.status(404).json({ error: "Book not found" });
  const { title, author, year, read } = req.body || {};
  if (title === undefined || !title.trim()) return res.status(400).json({ error: "title is required" });
  if (author === undefined || !author.trim()) return res.status(400).json({ error: "author is required" });
  const yearVal = (year !== undefined && year !== null && year !== "") ? parseInt(year, 10) : null;
  const readVal = (read !== undefined) ? (read ? 1 : 0) : existing.read;
  db.prepare("UPDATE books SET title=?, author=?, year=?, read=? WHERE id=?").run(title.trim(), author.trim(), yearVal, readVal, req.params.id);
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(req.params.id);
  res.json({ ...row, read: !!row.read });
});

// DELETE /api/books/:id
app.delete("/api/books/:id", (req, res) => {
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(req.params.id);
  if (!existing) return res.status(404).json({ error: "Book not found" });
  db.prepare("DELETE FROM books WHERE id = ?").run(req.params.id);
  res.json({ ok: true });
});

const PORT = parseInt(process.env.PORT, 10) || 3001;
app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "books-client",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.0"
  }
}
```

### client/vite.config.js
```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:3001"
    }
  }
});
```

### client/index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Books CRUD</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

### client/src/main.jsx
```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from "react";

const API = "/api/books";

function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState({ title: "", author: "", year: "", read: false });
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => fetch(API).then(r => r.json()).then(setBooks).catch(e => setMsg(e.message));

  useEffect(() => { load(); }, []);

  const handleCreate = () => {
    if (!form.title.trim() || !form.author.trim()) { setMsg("Title and author are required."); return; }
    const body = { title: form.title.trim(), author: form.author.trim(), year: form.year ? parseInt(form.year, 10) : null, read: form.read };
    fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(r => { if (!r.ok) throw new Error("Failed"); return r.json(); })
      .then(() => { setMsg("Book created."); setShowForm(false); resetForm(); load(); })
      .catch(e => setMsg(e.message));
  };

  const handleUpdate = () => {
    if (!form.title.trim() || !form.author.trim()) { setMsg("Title and author are required."); return; }
    const body = { title: form.title.trim(), author: form.author.trim(), year: form.year ? parseInt(form.year, 10) : null, read: form.read };
    fetch(`${API}/${editingId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(r => { if (!r.ok) throw new Error("Failed"); return r.json(); })
      .then(() => { setMsg("Book updated."); setEditingId(null); setShowForm(false); resetForm(); load(); })
      .catch(e => setMsg(e.message));
  };

  const handleToggleRead = (id, current) => {
    fetch(`${API}/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: "", author: "", read: !current }) })
      .catch(() => {});
    // Use a book reference to preserve title/author
    const book = books.find(b => b.id === id);
    if (book) {
      fetch(`${API}/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: book.title, author: book.author, year: book.year, read: !current }) })
        .then(r => { if (r.ok) load(); });
    }
  };

  const handleDelete = (id) => {
    fetch(`${API}/${id}`, { method: "DELETE" })
      .then(r => { if (r.ok) { setMsg("Book deleted."); load(); } });
  };

  const openEdit = (book) => {
    setForm({ title: book.title, author: book.author, year: book.year ? String(book.year) : "", read: book.read });
    setEditingId(book.id);
    setShowForm(true);
    setMsg("");
  };

  const resetForm = () => {
    setForm({ title: "", author: "", year: "", read: false });
    setEditingId(null);
    setShowForm(false);
    setMsg("");
  };

  return (
    <div className="container">
      <h1>Books</h1>
      {msg && <p className="msg">{msg}</p>}
      <button onClick={() => { resetForm(); setShowForm(true); }}>+ Add Book</button>

      {showForm && (
        <div className="form-panel">
          <h2>{editingId ? "Edit Book" : "New Book"}</h2>
          <div className="form-group">
            <label>Title</label>
            <input type="text" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Author</label>
            <input type="text" value={form.author} onChange={e => setForm({ ...form, author: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Year (optional)</label>
            <input type="number" value={form.year} onChange={e => setForm({ ...form, year: e.target.value })} />
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" checked={form.read} onChange={e => setForm({ ...form, read: e.target.checked })} /> Read
            </label>
          </div>
          <div className="form-actions">
            {editingId ? (
              <button onClick={handleUpdate}>Update</button>
            ) : (
              <button onClick={handleCreate}>Create</button>
            )}
            <button onClick={resetForm}>Cancel</button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map(b => (
            <tr key={b.id}>
              <td>{b.id}</td>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? ""}</td>
              <td>{b.read ? "✓" : "–"}</td>
              <td>
                <button onClick={() => handleToggleRead(b.id, b.read)}>Toggle</button>
                <button onClick={() => openEdit(b)}>Edit</button>
                <button onClick={() => handleDelete(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr><td colSpan="6">No books yet. Click "+ Add Book".</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```

### client/src/App.css
```css
* { box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 20px;
  background: #f5f5f5;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

h1 { color: #333; }

.msg {
  padding: 8px 12px;
  background: #fff3cd;
  border-radius: 4px;
  font-weight: 500;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.1);
}

th, td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background: #2c3e50;
  color: #fff;
}

tr:hover { background: #f9f9f9; }

button {
  padding: 5px 12px;
  margin: 2px;
  cursor: pointer;
  border: 1px solid #333;
  border-radius: 4px;
  background: #fff;
}

button:hover { background: #eee; }

.form-panel {
  margin-top: 20px;
  padding: 20px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
```