

The `better-sqlite3` native build fails on Node 26 (`node-gyp` can't compile against the new V8). I've swapped the SQLite layer to `sql.js`, which is pure JS/WASM in `node_modules` — no native compilation — and I also pinned `express` to a version that actually exists (there is no 4.21). These two files replace the originals:

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "sql.js": "^1.12.0"
  }
}
```

### server/index.js
```js
const path = require('path');
const fs = require('fs');
const initSqlJs = require('sql.js');
const express = require('express');

const DB_PATH = path.join(__dirname, 'data.db');

const app = express();
app.use(express.json());

function validate(body) {
  if (!body) return 'Invalid JSON body';
  const { title, author } = body;
  if (typeof title !== 'string' || title.trim() === '') return 'title is required and must be non-empty';
  if (typeof author !== 'string' || author.trim() === '') return 'author is required and must be non-empty';
  return null;
}

(async () => {
  const SQL = await initSqlJs();

  const db = fs.existsSync(DB_PATH)
    ? new SQL.Database(fs.readFileSync(DB_PATH))
    : new SQL.Database();

  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      "read" INTEGER NOT NULL DEFAULT 0
    );
  `);

  function persist() {
    fs.writeFileSync(DB_PATH, Buffer.from(db.export()));
  }

  function all(sql, params) {
    const rs = db.exec(sql, params);
    if (!rs || rs.length === 0) return [];
    const { columns, values } = rs[0];
    if (!values) return [];
    return values.map(vals => {
      const r = {};
      columns.forEach((c, i) => (r[c] = vals[i]));
      return r;
    });
  }

  function get(sql, params) {
    return all(sql, params)[0];
  }

  function run(sql, params) {
    db.run(sql, params);
    persist();
  }

  function lastId() {
    return get('SELECT last_insert_rowid() AS id').id;
  }

  function rowToJson(row) {
    return {
      id: row.id,
      title: row.title,
      author: row.author,
      year: row.year,
      read: Number(row.read) === 1,
    };
  }

  // GET /api/books
  app.get('/api/books', (_req, res) => {
    try {
      const rows = all('SELECT * FROM books ORDER BY id');
      res.json(rows.map(rowToJson));
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET /api/books/:id
  app.get('/api/books/:id', (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });
      const row = get('SELECT * FROM books WHERE id = ?', [id]);
      if (!row) return res.status(404).json({ error: 'Not found' });
      res.json(rowToJson(row));
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // POST /api/books
  app.post('/api/books', (req, res) => {
    try {
      const err = validate(req.body);
      if (err) return res.status(400).json({ error: err });

      const { title, author, year, read } = req.body;

      let yearVal = null;
      if (year !== undefined && year !== null && year !== '') {
        yearVal = Number(year);
        if (!Number.isInteger(yearVal)) return res.status(400).json({ error: 'year must be an integer' });
      }
      const readVal = (read === true || read === 1 || read === '1') ? 1 : 0;

      run(`INSERT INTO books (title, author, year, "read") VALUES (?, ?, ?, ?)`,
        [title.trim(), author.trim(), yearVal, readVal]);

      const row = get('SELECT * FROM books WHERE id = ?', [lastId()]);
      res.status(201).json(rowToJson(row));
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // PUT /api/books/:id
  app.put('/api/books/:id', (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });

      const existing = get('SELECT * FROM books WHERE id = ?', [id]);
      if (!existing) return res.status(404).json({ error: 'Not found' });

      const err = validate(req.body);
      if (err) return res.status(400).json({ error: err });

      const { title, author, year, read } = req.body;

      let yearVal = null;
      if (year !== undefined && year !== null && year !== '') {
        yearVal = Number(year);
        if (!Number.isInteger(yearVal)) return res.status(400).json({ error: 'year must be an integer' });
      }
      const readVal = (read === true || read === 1 || read === '1') ? 1 : 0;

      run(`UPDATE books SET title = ?, author = ?, year = ?, "read" = ? WHERE id = ?`,
        [title.trim(), author.trim(), yearVal, readVal, id]);

      const row = get('SELECT * FROM books WHERE id = ?', [id]);
      res.json(rowToJson(row));
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // DELETE /api/books/:id
  app.delete('/api/books/:id', (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });

      const existing = get('SELECT id FROM books WHERE id = ?', [id]);
      if (!existing) return res.status(404).json({ error: 'Not found' });

      run('DELETE FROM books WHERE id = ?', [id]);
      res.json({ deleted: true });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // ensure file exists even before first write
  persist();

  const PORT = process.env.PORT || 3001;
  app.listen(PORT, () => {
    console.log(`API server listening on http://localhost:${PORT}`);
  });
})();
```