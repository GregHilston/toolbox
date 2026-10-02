

### server/index.js
```javascript
const express = require('express');
const initSqlJs = require('sql.js');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const DB_PATH = path.join(__dirname, 'data.db');

// Initialize database
async function initDB() {
  const SQL = await initSqlJs();
  let db;
  
  // Load existing data if file exists
  if (fs.existsSync(DB_PATH)) {
    const fileBuffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(fileBuffer);
  } else {
    db = new SQL.Database();
  }

  // Create table
  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read INTEGER DEFAULT 0
    )
  `);

  // Save initial state
  saveDB(db);

  return db;
}

function saveDB(db) {
  const data = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(DB_PATH, buffer);
}

let dbPromise = initDB();

app.get('/api/books', async (req, res) => {
  try {
    const db = await dbPromise;
    const result = db.exec('SELECT * FROM books');
    
    // Handle empty result set
    if (!result || result.length === 0) {
      return res.json([]);
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    const books = rows.map(row => {
      const book = { id: row[0], title: row[1], author: row[2], year: row[3], read: Boolean(row[4]) };
      return book;
    });
    res.json(books);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

app.get('/api/books/:id', async (req, res) => {
  try {
    const db = await dbPromise;
    const result = db.exec('SELECT * FROM books WHERE id = ?', [req.params.id]);
    
    // Check if result exists and has rows
    if (!result || result.length === 0 || result[0].values.length === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    const row = result[0].values[0];
    res.json({
      id: row[0],
      title: row[1],
      author: row[2],
      year: row[3],
      read: Boolean(row[4])
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

app.post('/api/books', async (req, res) => {
  try {
    const db = await dbPromise;
    const { title, author, year, read } = req.body;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    db.run('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)', 
      [title.trim(), author.trim(), year || null, read ? 1 : 0]
    );
    
    // Get last inserted ID
    const result = db.exec('SELECT last_insert_rowid() as id');
    const lastId = result[0].values[0][0];
    
    const bookResult = db.exec('SELECT * FROM books WHERE id = ?', [lastId]);
    const newBook = bookResult[0].values[0];
    saveDB(db);
    
    res.status(201).json({
      id: newBook[0],
      title: newBook[1],
      author: newBook[2],
      year: newBook[3],
      read: Boolean(newBook[4])
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

app.put('/api/books/:id', async (req, res) => {
  try {
    const db = await dbPromise;
    const { title, author, year, read } = req.body;
    const id = req.params.id;

    // Check existence
    const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
    if (!result || result.length === 0 || result[0].values.length === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    db.run('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?', 
      [title.trim(), author.trim(), year || null, read ? 1 : 0, id]
    );
    
    const updatedBookResult = db.exec('SELECT * FROM books WHERE id = ?', [id]);
    const updatedBook = updatedBookResult[0].values[0];
    saveDB(db);
    
    res.json({
      id: updatedBook[0],
      title: updatedBook[1],
      author: updatedBook[2],
      year: updatedBook[3],
      read: Boolean(updatedBook[4])
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

app.delete('/api/books/:id', async (req, res) => {
  try {
    const db = await dbPromise;
    const id = req.params.id;
    
    const result = db.run('DELETE FROM books WHERE id = ?', [id]);
    
    // Check if any row was actually deleted
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    saveDB(db);
    
    res.json({ message: 'Book deleted' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

const PORT = process.env.PORT || 3001;
dbPromise.then(() => {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}).catch(err => {
  console.error('Failed to initialize database:', err);
});
```