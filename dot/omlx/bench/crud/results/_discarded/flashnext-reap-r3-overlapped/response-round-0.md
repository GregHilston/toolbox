

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.2.2",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```js
import express from "express";
import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const db = new Database(join(__dirname, "data.db"));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    "read" INTEGER NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

// GET all books
app.get("/api/books", (_req, res) => {
  const rows = db.prepare(`SELECT * FROM books ORDER BY id`).all();
  res.json(rows.map(mapRow));
});

// GET one book
app.get("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) {
    return res.status(404).json({ error: "Book not found" });
  }
  const row = db.prepare(`SELECT * FROM books WHERE id = ?`).get(id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(mapRow(row));
});

// POST create
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || typeof title !== "string" || title.trim() === "") {
    return res.status(400).json({ error: "title is required and must not be empty" });
  }
  if (!author || typeof author !== "string" || author.trim() === "") {
    return res.status(400).json({ error: "author is required and must not be empty" });
  }
  const yearVal = year === undefined || year === null || year === "" ? null : Number(year);
  const readVal = read ? 1 : 0;

  const info = db
    .prepare(`INSERT INTO books (title, author, year, "read") VALUES (?, ?, ?, ?)`)
    .run(title.trim(), author.trim(), yearVal, readVal);

  const row = db.prepare(`SELECT * FROM books WHERE id = ?`).get(info.lastInsertRowid);
  res.status(201).json(mapRow(row));
});

// PUT update
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const { title, author, year, read } = req.body;

  if (!title || typeof title !== "string" || title.trim() === "") {
    return res.status(400).json({ error: "title is required and must not be empty" });
  }
  if (!author || typeof author !== "string" || author.trim() === "") {
    return res.status(400).json({ error: "author is required and must not be empty" });
  }

  const existing = db.prepare(`SELECT * FROM books WHERE id = ?`).get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const yearVal = year === undefined || year === null || year === "" ? null : Number(year);
  const readVal = read ? 1 : 0;

  db.prepare(
    `UPDATE books SET title = ?, author = ?, year = ?, "read" = ? WHERE id = ?`
  ).run(title.trim(), author.trim(), yearVal, readVal, id);

  const row = db.prepare(`SELECT * FROM books WHERE id = ?`).get(id);
  res.json(mapRow(row));
});

// DELETE
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare(`SELECT * FROM books WHERE id = ?`).get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare(`DELETE FROM books WHERE id = ?`).run(id);
  res.status(204).end();
});

// ─── helpers ──────────────────────────────────────────────
function mapRow(row) {
  return { ...row, read: Boolean(row.read) };
}

const PORT = process.env.PORT ? Number(process.env.PORT) : 3001;
app.listen(PORT, () => {
  console.log(`API listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "client",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.5.0",
    "vite": "^6.3.4"
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
      "/api": "http://localhost:3001",
    },
  },
});
```

### client/index.html
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Book Shelf</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### client/src/main.jsx
```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from "react";

const API = "/api/books";

const empty = { title: "", author: "", year: "", read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [editingId, setEditingId] = useState(null); // null | "new" | number
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  /* ── data helpers ─────────────────────────────────── */
  const fetchBooks = useCallback(async () => {
    const res = await fetch(API);
    setBooks(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  /* ── CRUD actions ─────────────────────────────────── */
  async function save(e) {
    e.preventDefault();
    setError("");

    if (!form.title.trim()) { setError("Title is required."); return; }
    if (!form.author.trim()) { setError("Author is required."); return; }

    const body = {
      title: form.title.trim(),
      author: form.author.trim(),
      year: form.year === "" ? null : Number(form.year),
      read: form.read,
    };

    const isEdit = editingId !== null && editingId !== "new";
    const url = isEdit ? `${API}/${editingId}` : API;
    const method = isEdit ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "Request failed");
      return;
    }

    setEditingId(null);
    setForm(empty);
    fetchBooks();
  }

  async function deleteBook(id) {
    if (!confirm("Delete this book?")) return;
    const res = await fetch(`${API}/${id}`, { method: "DELETE" });
    if (res.status === 204 || res.ok) fetchBooks();
  }

  async function toggleRead(book) {
    const body = { ...book, read: !book.read };
    await fetch(`${API}/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    fetchBooks();
  }

  /* ── render helpers ───────────────────────────────── */
  function startEdit(book) {
    setEditingId(book.id);
    setForm({ title: book.title, author: book.author, year: book.year ?? "", read: book.read });
    setError("");
  }

  function startNew() {
    setEditingId("new");
    setForm(empty);
    setError("");
  }

  function cancel() {
    setEditingId(null);
    setForm(empty);
    setError("");
  }

  /* ── UI ───────────────────────────────────────────── */
  if (loading) return <p>Loading…</p>;

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>📚 Book Shelf</h1>

      {/* ── table ───────────────────────────────────────── */}
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
        <thead>
          <tr style={{ background: "#f0f0f0" }}>
            <th style={th}>Title</th>
            <th style={th}>Author</th>
            <th style={th}>Year</th>
            <th style={th}>Read</th>
            <th style={th}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 && (
            <tr><td colSpan={5} style={{ padding: 12 }}>No books yet.</td></tr>
          )}
          {books.map((b) => (
            <tr key={b.id} style={{ borderTop: "1px solid #ddd" }}>
              <td style={td}>{b.title}</td>
              <td style={td}>{b.author}</td>
              <td style={td}>{b.year ?? "—"}</td>
              <td style={td}>
                <button onClick={() => toggleRead(b)}>{b.read ? "✔" : "✘"}</button>
              </td>
              <td style={td}>
                <button onClick={() => startEdit(b)} style={{ marginRight: 6 }}>Edit</button>
                <button onClick={() => deleteBook(b.id)} style={{ color: "red" }}>Del</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── form ──────────────────────────────────────── */}
      {!editingId && (
        <button onClick={startNew} style={{ marginTop: 14, padding: "6px 14px" }}>
          + Add book
        </button>
      )}

      {editingId && (
        <form onSubmit={save} style={{ marginTop: 14, maxWidth: 420 }}>
          <h3>{editingId === "new" ? "Add book" : `Edit #${editingId}`}</h3>
          {error && <p style={{ color: "red" }}>{error}</p>}

          <label>
            Title *
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              style={inp}
            />
          </label>

          <label>
            Author *
            <input
              value={form.author}
              onChange={(e) => setForm({ ...form, author: e.target.value })}
              style={inp}
            />
          </label>

          <label>
            Year
            <input
              type="number"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
              style={inp}
            />
          </label>

          <label>
            Read
            <input
              type="checkbox"
              checked={form.read}
              onChange={(e) => setForm({ ...form, read: e.target.checked })}
            />
          </label>

          <div style={{ marginTop: 10 }}>
            <button type="submit">Save</button>{" "}
            <button type="button" onClick={cancel}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

/* ── tiny inline-style constants ────────────────────────── */
const th = { padding: 8, textAlign: "left" };
const td = { padding: 8 };
const inp = { display: "block", width: "100%", marginBottom: 8, padding: 4, boxSizing: "border-box" };
```

### README.md
```markdown
# Book Shelf

A minimal full-stack CRUD app managing a single `books` table in SQLite.

## Prerequisites

- Node.js 26+
- npm 10+

## Run the API server

```bash
cd server
npm install
npm start
```

The API listens on <http://localhost:3001> (or set `PORT` to override).

## Run the UI

In a **second** terminal:

```bash
cd client
npm install
npm run dev
```

Open <http://localhost:5173>.  Vite proxies `/api` → `http://localhost:3001`.

## Build the frontend for production

```bash
cd client
npm run build
```
```

---

**File summary (everything you need to place):**

| # | Path |
|---|------|
| 1 | `server/package.json` |
| 2 | `server/index.js` |
| 3 | `client/package.json` |
| 4 | `client/vite.config.js` |
| 5 | `client/index.html` |
| 6 | `client/src/main.jsx` |
| 7 | `client/src/App.jsx` |
| 8 | `README.md` |

### How to run (quick repeat)

```
# Terminal 1
cd server && npm install && npm start

# Terminal 2
cd client && npm install && npm run dev     # dev
cd client && npm install && npm run build    # production build
```

### Notes / gotchas

- `better-sqlite3` compiles a native addon during `npm install`; make sure you have a C++ toolchain (`build-essential` on Debian/Ubuntu, Xcode CLT on macOS, Visual Studio Build Tools on Windows).
- The SQLite database file `server/data.db` is created automatically on first start.
- `POST /api/books` with an empty/missing `title` or `author` → **400**.
- Any request targeting a non-existent `id` (`GET`, `PUT`, `DELETE`) → **404**.
- `DELETE` returns **204** (no body).  All other success paths return JSON.