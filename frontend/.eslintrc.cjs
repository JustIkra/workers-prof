/* eslint-env node */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {
    // Warn on console usage
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',

    // Vue specific
    'vue/multi-word-component-names': 'off',
    'vue/require-default-prop': 'warn',
    'vue/no-unused-vars': 'warn',

    // General
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
  },
}
