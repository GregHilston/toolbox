I installed and ran your app. These checks failed: server_starts, list, create, get_one, update, validation_400, not_found_404, delete, persists_restart, db_file, ui_list, ui_create, ui_toggle, ui_edit, ui_delete.

server npm install:
```
;
npm error       |         ^
npm error ./src/better_sqlite3.lzz:37:90: warning: 'Value' is deprecated: Use the version with the type tag. [-Wdeprecated-declarations]
npm error    37 |                 static_cast < Addon * > ( info . Data ( ) . As < v8 :: External > ( ) -> Value ( ) ) ->SqliteError.Reset( info . GetIsolate ( ) , SqliteError);
npm error       |                                                                                          ^
npm error /Users/ghilston/Library/Caches/node-gyp/26.10.0/include/node/v8-external.h:54:3: note: 'Value' has been explicitly marked deprecated here
npm error    54 |   V8_DEPRECATED("Use the version with the type tag.")
npm error       |   ^
npm error /Users/ghilston/Library/Caches/node-gyp/26.10.0/include/node/v8config.h:615:35: note: expanded from macro 'V8_DEPRECATED'
npm error   615 | # define V8_DEPRECATED(message) [[deprecated(message)]]
npm error       |                                   ^
npm error 14 warnings and 6 errors generated.
npm error make: *** [better_sqlite3.target.mk:140: Release/obj.target/better_sqlite3/src/better_sqlite3.o] Error 1
npm error gyp ERR! build error 
npm error gyp ERR! stack Error: `make` failed with exit code: 2
npm error gyp ERR! stack at ChildProcess.<anonymous> (/Users/ghilston/.hermes/node/lib/node_modules/npm/node_modules/node-gyp/lib/build.js:219:23)
npm error gyp ERR! System Darwin 27.0.0
npm error gyp ERR! command "/Users/ghilston/.hermes/node/bin/node" "/Users/ghilston/.hermes/node/lib/node_modules/npm/node_modules/node-gyp/bin/node-gyp.js" "rebuild" "--release"
npm error gyp ERR! cwd /private/tmp/crud-eval/flashnext-reap-r3/app/server/node_modules/better-sqlite3
npm error gyp ERR! node -v v26.10.0
npm error gyp ERR! node-gyp -v v12.4.0
npm error gyp ERR! $npm_package_name better-sqlite3
npm error gyp ERR! $npm_package_version 11.10.0
npm error gyp ERR! not ok
npm error A complete log of this run can be found in: /Users/ghilston/.npm/_logs/2026-10-02T13_44_34_959Z-debug-0.log
```

Fix the problems. Output only the files you change, in full, in the same format as before.