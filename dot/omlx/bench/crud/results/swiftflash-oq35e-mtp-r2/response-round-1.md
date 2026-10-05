

### client/src/App.jsx
```jsx
import { useState, useEffect } from "react";

const API = "/api/books";

function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState({ title: "", author: "", year: "", read: false });
  const [editingId, setEditingId] = useState(null);
  const [msg, setMsg] = useState("");

  const load = () => fetch(API).then(r => r.json()).then(setBooks).catch(e => setMsg(e.message));

  useEffect(() => { load(); }, []);

  const handleCreate = () => {
    if (!form.title.trim() || !form.author.trim()) { setMsg("Title and author are required."); return; }
    const body = { title: form.title.trim(), author: form.author.trim(), year: form.year ? parseInt(form.year, 10) : null, read: form.read };
    fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(r => { if (!r.ok) throw new Error("Failed"); return r.json(); })
      .then(() => { setMsg("Book created."); resetForm(); load(); })
      .catch(e => setMsg(e.message));
  };

  const handleUpdate = () => {
    if (!form.title.trim() || !form.author.trim()) { setMsg("Title and author are required."); return; }
    const body = { title: form.title.trim(), author: form.author.trim(), year: form.year ? parseInt(form.year, 10) : null, read: form.read };
    fetch(`${API}/${editingId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(r => { if (!r.ok) throw new Error("Failed"); return r.json(); })
      .then(() => { setMsg("Book updated."); resetForm(); load(); })
      .catch(e => setMsg(e.message));
  };

  const handleToggleRead = (id, current) => {
    const book = books.find(b => b.id === id);
    if (!book) return;
    fetch(`${API}/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: book.title, author: book.author, year: book.year, read: !current })
    }).then(r => { if (r.ok) load(); });
  };

  const handleDelete = (id) => {
    fetch(`${API}/${id}`, { method: "DELETE" })
      .then(r => { if (r.ok) { setMsg("Book deleted."); load(); } });
  };

  const openEdit = (book) => {
    setForm({ title: book.title, author: book.author, year: book.year ? String(book.year) : "", read: book.read });
    setEditingId(book.id);
    setMsg("");
  };

  const resetForm = () => {
    setForm({ title: "", author: "", year: "", read: false });
    setEditingId(null);
    setMsg("");
  };

  return (
    <div className="container">
      <h1>Books</h1>
      {msg && <p className="msg">{msg}</p>}

      <div className="form-panel">
        <h2>{editingId ? "Edit Book" : "Add Book"}</h2>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            name="title"
            type="text"
            placeholder="Title"
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="author">Author</label>
          <input
            id="author"
            name="author"
            type="text"
            placeholder="Author"
            value={form.author}
            onChange={e => setForm({ ...form, author: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="year">Year (optional)</label>
          <input
            id="year"
            name="year"
            type="number"
            placeholder="Year"
            value={form.year}
            onChange={e => setForm({ ...form, year: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="read">
            <input
              id="read"
              name="read"
              type="checkbox"
              checked={form.read}
              onChange={e => setForm({ ...form, read: e.target.checked })}
            /> Read
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
            <tr><td colSpan="6">No books yet.</td></tr>
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