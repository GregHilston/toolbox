

The test automation can't find title/author inputs because the form is hidden behind a "+ Add Book" button click. The fix is to make the "Add Book" form always visible on the page.

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';

const API = '/api/books';

function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [read, setRead] = useState(false);
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    const res = await fetch(API);
    const data = await res.json();
    setBooks(data);
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const openEdit = (book) => {
    setTitle(book.title);
    setAuthor(book.author);
    setYear(book.year != null ? String(book.year) : '');
    setRead(!!book.read);
    setEditing(book);
    setError('');
  };

  const cancelEdit = () => {
    setTitle('');
    setAuthor('');
    setYear('');
    setRead(false);
    setEditing(null);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const body = {
      title,
      author,
      year: year !== '' ? parseInt(year, 10) : null,
      read,
    };

    const url = editing ? `${API}/${editing.id}` : API;
    const method = editing ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      setError(err.error || 'An error occurred');
      return;
    }

    await fetchBooks();
    cancelEdit();
  };

  const toggleRead = async (book) => {
    const res = await fetch(`${API}/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: book.title,
        author: book.author,
        year: book.year,
        read: !book.read,
      }),
    });
    if (res.ok) fetchBooks();
  };

  const handleDelete = async (book) => {
    if (!window.confirm(`Delete "${book.title}"?`)) return;
    const res = await fetch(`${API}/${book.id}`, { method: 'DELETE' });
    if (res.ok) fetchBooks();
  };

  return (
    <div>
      <h1>📚 Books</h1>

      <form onSubmit={handleSubmit}>
        <h2>{editing ? `Edit Book #${editing.id}` : 'Add Book'}</h2>

        <label>
          <span>Title</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </label>

        <label>
          <span>Author</span>
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            required
          />
        </label>

        <label>
          <span>Year</span>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </label>

        <label>
          <span>Read</span>
          <input
            type="checkbox"
            checked={read}
            onChange={(e) => setRead(e.target.checked)}
          />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit">{editing ? 'Update' : 'Create'}</button>
          {editing && (
            <button type="button" onClick={cancelEdit}>Cancel</button>
          )}
        </div>
      </form>

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
          {books.map((book) => (
            <tr key={book.id}>
              <td>{book.id}</td>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? '—'}</td>
              <td>{book.read ? '✅' : '📖'}</td>
              <td>
                <button
                  className={`toggle ${book.read ? 'is-read' : ''}`}
                  onClick={() => toggleRead(book)}
                >
                  {book.read ? 'Unread' : 'Read'}
                </button>
                <button className="edit" onClick={() => openEdit(book)}>
                  Edit
                </button>
                <button className="delete" onClick={() => handleDelete(book)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', color: '#999' }}>
                No books yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```