# E-commerce Project Type

## Extra folder

Adds `catalog/` folder for product info, pricing, inventory.

```
project/
└── catalog/
    ├── products.json
    ├── pricing.md
    └── categories.md
```

## CLAUDE.md additions

Add this section to the project's CLAUDE.md after Task Routing:

```markdown
### Working on products or catalog
1. Read `project/catalog/products.json` for current product list
2. Read `docs/context/PRODUCT-STRATEGY.md` for positioning
```

## Initial doc stubs

When scaffolding an e-commerce project, create these starter docs:
- `docs/context/PRODUCT-STRATEGY.md` (placeholder)
- `docs/workflows/ORDER-FLOW.md` (placeholder)
- `docs/reference/PAYMENT-PROVIDER.md` (placeholder)
