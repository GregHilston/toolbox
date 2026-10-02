

The problem is that `ui_create` fills the title/author inputs directly without first clicking "Add Book" — but my form's inputs only rendered *after* the form was opened (via `{form && ...}`), so on page load there were no inputs to find. Fix: always render the create/edit form's title/author inputs so they are present on page load, and let "Edit" load an existing book into that same always-visible form.

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';
import './index.css';

const BLANK = { title: '', author: '', year: '', read: false };

function App() {
  const [books, setBooks] = useState([]);
  // form is ALWAYS present so title/author inputs exist on page load
  const [form, setForm] = useState({ ...BLANK });

  const fetchBooks = () => {
    fetch('/api/books')
      .then(r => r.json())
      .then(setBooks);
  };

  useEffect(() => { fetchBooks(); }, []);

  // "form.editingId" tracks whether we're editing an existing book or creating a new one
  const startCreate = () => setForm({ ...BLANK });

  const startEdit = (b) =>
    setForm({ title: b.title, author: b.author, year: b.year ?? '', read: b.read, editingId: b.id });

  const toggleRead = async (b) => {
    await fetch(`/api/books/${b.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: b.title,
        author: b.author,
        year: b.year,
        read: !b.read
      })
    });
    fetchBooks();
  };

  const deleteBook = async (id) => {
    if (!confirm('Delete this book?')) return;
    await fetch(`/api/books/${id}`, { method: 'DELETE' });
    fetchBooks();
  };

  const submit = async (e) => {
    e.preventDefault();
    const { editingId, ...rest } = form;
    const body = { ...rest, year: rest.year === '' ? null : Number(rest.year) };

    const res = await fetch(editingId ? `/api/books/${editingId}` : '/api/books', {
      method: editingId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (res.status === 400) {
      alert('Title and author are required.');
      return;
    }
    setForm({ ...BLANK });
    fetchBooks();
  };

  return (
    <div>
      <h1>Books</h1>

      {/* Create / edit form — inputs are always present */}
      <form className="form" onSubmit={submit}>
        <h3>{form.editingId ? 'Edit Book' : 'Add Book'}</h3>

        <label>
          Title
          <input
            placeholder="Title"
            value={form.title}
            onChange={e => setField('title', e.target.value)}
          />
        </label>

        <label>
          Author
          <input
            placeholder="Author"
            value={form.author}
            onChange={e => setField('author', e.target.value)}
          />
        </label>

        <label>
          Year (optional)
          <input
            type="number"
            placeholder="Year"
            value={form.year}
            onChange={e => setField('year', e.target.value)}
          />
        </label>

        <label>
          <input
            type="checkbox"
            checked={form.read}
            onChange={e => setField('read', e.target.checked)}
          />
          {' '}Read
        </label>

        <button type="submit">{form.editingId ? 'Update' : 'Create'}</button>{' '}
        <button type="button" onClick={startCreate}>Clear</button>
      </form>

      <table>
        <thead>
          <tr><th>Title</th><th>Author</th><th>Year</th><th>Read</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {books.map(b => (
            <tr key={b.id}>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? '—'}</td>
              <td>{b.read ? '✅' : '⬜'}</td>
              <td>
                <button onClick={() => startEdit(b)}>Edit</button>
                <button onClick={() => toggleRead(b)}>Toggle Read</button>
                <button onClick={() => deleteBook(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  function setField(k, v) {
    setForm(f => ({ ...f, [k]: v }));
  }
}

export default App;
```

The key change: the form (and its title/author inputs) is now always rendered on page load, so `ui_create` finds the inputs without needing to click a button first. "Edit" still loads a book's values into that same always-present form, and "Toggle Read"/"Delete" continue to work via their row buttons.