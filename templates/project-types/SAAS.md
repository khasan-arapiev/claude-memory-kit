# SaaS / Application Project Type

## Extra folder

Adds `api/` folder for endpoint specs, schemas, integration docs.

```
project/
└── api/
    ├── endpoints.md
    ├── auth.md
    └── schemas/
```

## CLAUDE.md additions

Add **all three** of these routing entries to the project's CLAUDE.md after Task Routing. Every stub doc must be routed, otherwise the audit will flag it as an orphan immediately after scaffold.

```markdown
### Working on API or endpoints
1. Read `docs/architecture/API-OVERVIEW.md`
2. Read `project/api/endpoints.md` for current spec

### Working on data model / database
1. Read `docs/architecture/DATA-MODEL.md`

### Deploying or releasing
1. Read `docs/workflows/DEPLOYMENT.md`
```

## Initial doc stubs

When scaffolding a SaaS project, create these starter docs (all are routed above):
- `docs/architecture/API-OVERVIEW.md` (placeholder)
- `docs/architecture/DATA-MODEL.md` (placeholder)
- `docs/workflows/DEPLOYMENT.md` (placeholder)
- `project/api/endpoints.md` (placeholder)
