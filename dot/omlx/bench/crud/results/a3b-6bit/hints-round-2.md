I installed and ran your app. These checks failed: server_starts, list, create, get_one, update, validation_400, not_found_404, delete, persists_restart, db_file, ui_list, ui_create, ui_toggle, ui_edit, ui_delete.

server log:
```
> book-manager-server@1.0.0 start
> node index.js

failed to asynchronously prepare wasm: Error: ENOENT: no such file or directory, open 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.wasm'
Aborted(Error: ENOENT: no such file or directory, open 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.wasm')
Failed to initialize server: Error: Error: ENOENT: no such file or directory, open 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.wasm'
    at Module.onAbort (/private/tmp/crud-eval/a3b-6bit/app/server/node_modules/sql.js/dist/sql-wasm.js:40:20)
    at Na (/private/tmp/crud-eval/a3b-6bit/app/server/node_modules/sql.js/dist/sql-wasm.js:98:268)
    at Qa (/private/tmp/crud-eval/a3b-6bit/app/server/node_modules/sql.js/dist/sql-wasm.js:99:350)
    at async /private/tmp/crud-eval/a3b-6bit/app/server/node_modules/sql.js/dist/sql-wasm.js:164:81
```

Fix the problems. Output only the files you change, in full, in the same format as before.