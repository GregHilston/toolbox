// Tiny typed program proving the flake's Node + TypeScript are on PATH.
// Compile and run:  tsc hello.ts && node hello.js
// Both `tsc` and `node` come from the flake's dev shell.

function greet(name: string): string {
  return `Hello, ${name}! The TypeScript dev shell works.`;
}

console.log(greet("world"));
