

The `ui_delete` test expects the standard native browser confirm dialog (the harness auto-accepts it). My custom in-table confirmation row broke the clickable flow. Switching to `window.confirm()` so Delete triggers a native dialog the test can handle.

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

  /* ---------- delete (native confirm dialog) ---------- */
  const deleteBook = (book) => {
    if (!window.confirm(`Delete "${book.title}"?`)) return;
    fetch(`${API}/${book.id}`, { method: "DELETE" })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.error); });
        return r.json();
      })
      .then(() => load())
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
                    <button onClick={() => deleteBook(book)}>Delete</button>
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