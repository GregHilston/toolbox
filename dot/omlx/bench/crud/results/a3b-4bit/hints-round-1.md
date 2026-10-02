I installed and ran your app. These checks failed: server_starts, list, create, get_one, update, validation_400, not_found_404, delete, persists_restart, db_file, ui_list, ui_create, ui_toggle, ui_edit, ui_delete.

server npm install:
```
npm error gyp info spawn args '-Dnode_root_dir=/Users/ghilston/Library/Caches/node-gyp/26.10.0',
npm error gyp info spawn args '-Dnode_gyp_dir=/Users/ghilston/.hermes/node/lib/node_modules/npm/node_modules/node-gyp',
npm error gyp info spawn args '-Dnode_lib_file=/Users/ghilston/Library/Caches/node-gyp/26.10.0/<(target_arch)/node.lib',
npm error gyp info spawn args '-Dmodule_root_dir=/private/tmp/crud-eval/a3b-4bit/app/server/node_modules/better-sqlite3',
npm error gyp info spawn args '-Dnode_engine=v8',
npm error gyp info spawn args '--depth=.',
npm error gyp info spawn args '--no-parallel',
npm error gyp info spawn args '--generator-output',
npm error gyp info spawn args 'build',
npm error gyp info spawn args '-Goutput_dir=.'
npm error gyp info spawn args ]
npm error gyp info spawn make
npm error gyp info spawn args [ 'BUILDTYPE=Release', '-C', 'build' ]
npm error g++: error: unrecognized command-line option '-stdlib=libc++'
npm error g++: error: unrecognized command-line option '-stdlib=libc++'
npm error make: *** [better_sqlite3.target.mk:140: Release/obj.target/better_sqlite3/src/better_sqlite3.o] Error 1
npm error gyp ERR! build error 
npm error gyp ERR! stack Error: `make` failed with exit code: 2
npm error gyp ERR! stack at ChildProcess.<anonymous> (/Users/ghilston/.hermes/node/lib/node_modules/npm/node_modules/node-gyp/lib/build.js:219:23)
npm error gyp ERR! System Darwin 27.0.0
npm error gyp ERR! command "/Users/ghilston/.hermes/node/bin/node" "/Users/ghilston/.hermes/node/lib/node_modules/npm/node_modules/node-gyp/bin/node-gyp.js" "rebuild" "--release"
npm error gyp ERR! cwd /private/tmp/crud-eval/a3b-4bit/app/server/node_modules/better-sqlite3
npm error gyp ERR! node -v v26.10.0
npm error gyp ERR! node-gyp -v v12.4.0
npm error gyp ERR! $npm_package_name better-sqlite3
npm error gyp ERR! $npm_package_version 9.6.0
npm error gyp ERR! not ok
npm error A complete log of this run can be found in: /Users/ghilston/.npm/_logs/2026-10-02T11_21_30_099Z-debug-0.log
```

Fix the problems. Output only the files you change, in full, in the same format as before.