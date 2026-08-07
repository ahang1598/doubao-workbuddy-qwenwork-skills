import { readFileSync } from "node:fs";

export const contentTokens = JSON.parse(readFileSync(new URL("./content-tokens.json", import.meta.url), "utf8"));
