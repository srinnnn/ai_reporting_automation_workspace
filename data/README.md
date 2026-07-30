# Data Directory Convention

This repository separates code from business data.

```text
data/
├── examples/   desensitized sample data allowed in Git
├── templates/  reusable input templates allowed in Git
└── local/      real local business data, never uploaded
```

Rules:

- Put real Anta, Meituan, JD, Tmall, mini-program, official-site, CRM, and operation files under `data/local/` or another ignored local folder.
- Put only desensitized test files under `data/examples/`.
- Put only blank or generic templates under `data/templates/`.
- Do not store API keys, cookies, passwords, or account credentials in any data file.
