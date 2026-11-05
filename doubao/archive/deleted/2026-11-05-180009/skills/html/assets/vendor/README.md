# Vendored parser

Acorn 8.19.0 (MIT), copied without modification from `acorn@8.19.0` on npm.
Source: https://github.com/acornjs/acorn/tree/8.19.0/acorn

`acorn.cjs` is the upstream `dist/acorn.js`, renamed for explicit CommonJS loading.
SHA-256: b95392d79457d0357555c5ed3e56302d074b92dff119bcf3b44179500b10e9df

Used by `scripts/check-unused-anonymous.cjs` to parse JavaScript without executing page code. The package is local; no runtime install or network fetch is required.
