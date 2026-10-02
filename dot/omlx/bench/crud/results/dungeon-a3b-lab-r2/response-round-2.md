### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    author: '',
    year: '',
    read: false
  });
  const [formErrors, setFormErrors] = useState({});

  // Fetch books on component mount
  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/books');
      if (!response.ok) {
        throw new Error('Failed to fetch books');
      }
      const data = await response.json();
      setBooks(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching books:', err);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.title || formData.title.trim() === '') {
      errors.title = 'Title is required';
    }
    
    if (!formData.author || formData.author.trim() === '') {
      errors.author = 'Author is required';
    }
    
    if (formData.year !== '' && (isNaN(formData.year) || Number(formData.year) < 0)) {
      errors.year = 'Year must be a positive number or empty';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const response = await fetch('/api/books', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: formData.title.trim(),
          author: formData.author.trim(),
          year: formData.year ? Number(formData.year) : null,
          read: formData.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create book');
      }
      
      const newBook = await response.json();
      setBooks(prev => [...prev, newBook]);
      resetForm();
      setShowForm(false);
    } catch (err) {
      setError(err.message);
      console.error('Error creating book:', err);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const response = await fetch(`/api/books/${editingBook.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: formData.title.trim(),
          author: formData.author.trim(),
          year: formData.year ? Number(formData.year) : null,
          read: formData.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update book');
      }
      
      const updatedBook = await response.json();
      setBooks(prev => 
        prev.map(book => 
          book.id === updatedBook.id ? updatedBook : book
        )
      );
      resetForm();
      setShowForm(false);
      setEditingBook(null);
    } catch (err) {
      setError(err.message);
      console.error('Error updating book:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this book?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/books/${id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete book');
      }
      
      setBooks(prev => prev.filter(book => book.id !== id));
    } catch (err) {
      setError(err.message);
      console.error('Error deleting book:', err);
    }
  };

  const handleToggleRead = async (book) => {
    try {
      const response = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...book,
          read: !book.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update book');
      }
      
      const updatedBook = await response.json();
      setBooks(prev => 
        prev.map(b => 
          b.id === updatedBook.id ? updatedBook : b
        )
      );
    } catch (err) {
      setError(err.message);
      console.error('Error toggling read status:', err);
    }
  };

  const openEditForm = (book) => {
    setEditingBook(book);
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year ? String(book.year) : '',
      read: book.read
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      author: '',
      year: '',
      read: false
    });
    setFormErrors({});
    setEditingBook(null);
  };

  const openCreateForm = () => {
    resetForm();
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    resetForm();
  };

  if (loading) {
    return (
      <div className="container">
        <header>
          <h1>📚 Book Manager</h1>
          <p>Loading books...</p>
        </header>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <h1>📚 Book Manager</h1>
        <p>Manage your book collection</p>
      </header>

      {error && (
        <div style={{
          backgroundColor: '#fde8e8',
          color: '#e74c3c',
          padding: '10px 15px',
          borderRadius: '4px',
          marginBottom: '20px',
          border: '1px solid #f5c6cb'
        }}>
          {error}
        </div>
      )}

      <div className="controls">
        <h2>All Books ({books.length})</h2>
        <button 
          onClick={openCreateForm}
          className="btn btn-primary"
        >
          + Add New Book
        </button>
      </div>

      {books.length === 0 ? (
        <div className="empty-state">
          <p>No books found. Add your first book to get started!</p>
        </div>
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
            {books.map(book => (
              <tr key={book.id}>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year || 'N/A'}</td>
                <td>
                  <span className={book.read ? 'read-yes' : 'read-no'}>
                    {book.read ? '✓ Yes' : '✗ No'}
                  </span>
                </td>
                <td>
                  <div className="actions">
                    <button
                      onClick={() => handleToggleRead(book)}
                      className="btn btn-success"
                      title="Toggle Read Status"
                    >
                      {book.read ? 'Unread' : 'Read'}
                    </button>
                    <button
                      onClick={() => openEditForm(book)}
                      className="btn btn-warning"
                      title="Edit Book"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(book.id)}
                      className="btn btn-danger"
                      title="Delete Book"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="form-modal" onClick={closeForm}>
          <div className="form-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingBook ? 'Edit Book' : 'Add New Book'}</h2>
            
            <form onSubmit={editingBook ? handleUpdate : handleSubmit}>
              <div className="form-group">
                <label htmlFor="title">Title *</label>
                <input
                  type="text"
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleInputChange('title', e.target.value)}
                  placeholder="Enter book title"
                />
                {formErrors.title && (
                  <span className="error">{formErrors.title}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="author">Author *</label>
                <input
                  type="text"
                  id="author"
                  value={formData.author}
                  onChange={(e) => handleInputChange('author', e.target.value)}
                  placeholder="Enter author name"
                />
                {formErrors.author && (
                  <span className="error">{formErrors.author}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="year">Year (optional)</label>
                <input
                  type="number"
                  id="year"
                  value={formData.year}
                  onChange={(e) => handleInputChange('year', e.target.value)}
                  placeholder="Enter publication year"
                  min="0"
                />
                {formErrors.year && (
                  <span className="error">{formErrors.year}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="read">Read Status</label>
                <select
                  id="read"
                  value={formData.read ? 'true' : 'false'}
                  onChange={(e) => handleInputChange('read', e.target.value === 'true')}
                >
                  <option value="false">Not Read</option>
                  <option value="true">Read</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={closeForm}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                >
                  {editingBook ? 'Update Book' : 'Create Book'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
```