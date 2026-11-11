export default [
  {
    files: ["portfolio/app/static/**/*.{js,mjs,cjs}", "tests/**/*.{js,mjs,cjs}"],
    languageOptions: { ecmaVersion: "latest" },
    rules: {
      "no-dupe-keys": "error",
      "no-unreachable": "error",
      "no-constant-condition": ["error", { checkLoops: false }],
      "no-duplicate-case": "error",
      "no-self-assign": "error"
    }
  }
];
