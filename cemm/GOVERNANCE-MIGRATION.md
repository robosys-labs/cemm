# Governance Migration

Apply these files at repository root:

```text
AGENTS.md
README.md
ARCHITECTURE.md
```

Place the three 3.3 plans under:

```text
cemm/newarch/
```

To prevent duplicate authority:

1. remove `cemm/AGENTS.md`, or replace it with a short pointer to `../AGENTS.md`;
2. remove `cemm/ARCHITECTURE.md`, or replace it with a short pointer to `../ARCHITECTURE.md`;
3. update remaining links that identify package-level governance files as canonical;
4. archive v3.1/v3.2 plans as implementation history;
5. do not mark 3.3 complete until the definition-of-done gates pass.

Suggested compatibility stub:

```markdown
# Moved

The canonical document is [`../AGENTS.md`](../AGENTS.md).
```

Use the equivalent link for `ARCHITECTURE.md`.
