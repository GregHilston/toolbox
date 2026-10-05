

The root cause is a missing `express.json()` middleware (so `req.body` was always `undefined`), plus the create form was hidden behind a toggle so tests couldn't find the inputs. Fixing both:

### server/index.js
```js
const express = require("express");
const Database = require("better-sqlite3");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

const db = new Database(path.join(__dirname, "data.db"));
db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    read   BOOLEAN DEFAULT 0
  );
`);

// GET all books
app.get("/api/books", (req, res) => {
  const books = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(books);
});

// GET one book
app.get("/api/books/:id", (req, res) => {
  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(Number(req.params.id));
  if (!book) return res.status(404).json({ error: "Book not found" });
  res.json(book);
});

// POST create book
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body || {};

  if (!title || typeof title !== "string" || title.trim() === "") {
    return res.status(400).json({ error: "Title is required" });
  }
  if (!author || typeof author !== "string" || author.trim() === "") {
    return res.status(400).json({ error: "Author is required" });
  }

  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(title.trim(), author.trim(), year != null ? Number(year) : null, read ? 1 : 0);

  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json(book);
});

// PUT update book
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const body = req.body || {};
  const title = body.title !== undefined ? body.title : existing.title;
  const author = body.author !== undefined ? body.author : existing.author;
  const year = body.year !== undefined ? (body.year === "" ? null : Number(body.year)) : existing.year;
  const read = body.read !== undefined ? (body.read ? 1 : 0) : existing.read;

  if (!title || typeof title !== "string" || title.trim() === "") {
    return res.status(400).json({ error: "Title cannot be empty" });
  }
  if (!author || typeof author !== "string" || author.trim() === "") {
    return res.status(400).json({ error: "Author cannot be empty" });
  }

  db.prepare("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?")
    .run(title.trim(), author.trim(), year, read, id);

  const updated = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json(updated);
});

// DELETE book
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ message: "Book deleted" });
});

app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### client/src/App.jsx
```jsx
import { useEffect, useState } from "react";
import "./App.css";

const API = "/api/books";

export default function App() {
  const [books, setBooks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // create form – always visible
  const [cTitle, setCTitle] = useState("");
  const [cAuthor, setCAuthor] = useState("");
  const [cYear, setCYear] = useState("");

  // edit – the id currently in "edit mode", null means not editing
  const [editId, setEditId] = useState(null);
  const [eTitle, setETitle] = useState("");
  const [eAuthor, setEAuthor] = useState("");
  const [eYear, setEYear] = useState("");
  const [eRead, setERead] = useState(false);

  // delete – the id whose confirmation dialog is open
  const [delId, setDelId] = useState(null);

  const load = () => {
    setLoading(true);
    fetch(API)
      .then((r) => r.json())
      .then((data) => {
        setBooks(data);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  /* ---------- create ---------- */
  const submitCreate = (e) => {
    e.preventDefault();
    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: cTitle.trim(),
        author: cAuthor.trim(),
        year: cYear ? Number(cYear) : null,
        read: false,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.error); });
        return r.json();
      })
      .then(() => {
        setCTitle("");
        setCAuthor("");
        setCYear("");
        setError("");
        load();
      })
      .catch((e) => setError(e.message));
  };

  /* ---------- toggle read ---------- */
  const toggleRead = (book) => {
    fetch(`${API}/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read: !book.read }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.error); });
        return r.json();
      })
      .then(() => load())
      .catch((e) => setError(e.message));
  };

  /* ---------- edit ---------- */
  const startEdit = (book) => {
    setEditId(book.id);
    setETitle(book.title);
    setEAuthor(book.author);
    setEYear(book.year != null ? String(book.year) : "");
    setERead(!!book.read);
  };

  const saveEdit = (e) => {
    e.preventDefault();
    fetch(`${API}/${editId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: eTitle.trim(),
        author: eAuthor.trim(),
        year: eYear ? Number(eYear) : null,
        read: eRead,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.error); });
        return r.json();
      })
      .then(() => {
        setEditId(null);
        load();
      })
      .catch((e) => setError(e.message));
  };

  /* ---------- delete ---------- */
  const confirmDelete = () => {
    fetch(`${API}/${delId}`, { method: "DELETE" })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.error); });
        setDelId(null);
        load();
      })
      .catch((e) => setError(e.message));
  };

  return (
    <div className="wrapper">
      <h1>Bookshelf</h1>

      {error && <p className="msg error">{error}</p>}

      {/* ---- always-visible create form ---- */}
      <form onSubmit={submitCreate} className="toolbar">
        <input
          placeholder="Title"
          value={cTitle}
          onChange={(e) => setCTitle(e.target.value)}
          required
        />
        <input
          placeholder="Author"
          value={cAuthor}
          onChange={(e) => setCAuthor(e.target.value)}
          required
        />
        <input
          placeholder="Year"
          type="number"
          value={cYear}
          onChange={(e) => setCYear(e.target.value)}
          style={{ width: 80 }}
        />
        <button type="submit">Add Book</button>
      </form>

      {/* ---- books table ---- */}
      {loading ? (
        <p className="msg">Loading…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Author</th>
              <th>Year</th>
              <th>Read</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {books.length === 0 && (
              <tr><td colSpan="5" className="msg">No books yet.</td></tr>
            )}
            {books.map((book) => {
              // ----- edit row -----
              if (book.id === editId) {
                return (
                  <tr key={book.id}>
                    <td>
                      <input
                        placeholder="Title"
                        value={eTitle}
                        onChange={(e) => setETitle(e.target.value)}
                        required
                      />
                    </td>
                    <td>
                      <input
                        placeholder="Author"
                        value={eAuthor}
                        onChange={(e) => setEAuthor(e.target.value)}
                        required
                      />
                    </td>
                    <td>
                      <input
                        placeholder="Year"
                        type="number"
                        value={eYear}
                        onChange={(e) => setEYear(e.target.value)}
                        style={{ width: 70 }}
                      />
                    </td>
                    <td>
                      <label>
                        <input
                          type="checkbox"
                          checked={eRead}
                          onChange={(e) => setERead(e.target.checked)}
                        />{" "}
                        Read
                      </label>
                    </td>
                    <td>
                      <button onClick={saveEdit}>Save</button>{" "}
                      <button onClick={() => setEditId(null)}>Cancel</button>
                    </td>
                  </tr>
                );
              }

              // ----- delete confirmation -----
              if (book.id === delId) {
                return (
                  <tr key={book.id}>
                    <td colSpan="5">
                      Delete "&nbsp;{book.title}&nbsp;"?{" "}
                      <button onClick={confirmDelete}>Yes, Delete</button>{" "}
                      <button onClick={() => setDelId(null)}>Cancel</button>
                    </td>
                  </tr>
                );
              }

              // ----- normal row -----
              return (
                <tr key={book.id}>
                  <td>{book.title}</td>
                  <td>{book.author}</td>
                  <td>{book.year != null ? book.year : ""}</td>
                  <td>{book.read ? "Read" : "Unread"}</td>
                  <td>
                    <button onClick={() => toggleRead(book)}>
                      {book.read ? "Mark Unread" : "Mark Read"}
                    </button>{" "}
                    <button onClick={() => startEdit(book)}>Edit</button>{" "}
                    <button onClick={() => setDelId(book.id)}>Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

### client/src/App.css
```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #1a1a1a;
}

.wrapper {
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1rem;
}

h1 {
  margin-bottom: 1.5rem;
}

.msg {
  padding: 0.5rem;
  text-align: center;
}

.msg.error {
  color: #d32f2f;
  background: #ffebee;
  border-radius: 4px;
}

/* toolbar / create form */
.toolbar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar input {
  padding: 0.45rem 0.65rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

button {
  padding: 0.4rem 0.85rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 0.95rem;
}

button:hover {
  background: #e8e8e8;
}

/* table */
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

th, td {
  padding: 0.65rem 0.8rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}

th {
  background: #fafafa;
  font-weight: 600;
}

td input {
  padding: 0.35rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 3px;
  font-size: 0.95rem;
}
```