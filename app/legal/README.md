# Legal Knowledge Base

Reference content for grounding mock jury simulations. This is illustrative
reference material for a research/training tool, **not legal advice**.

```
legal/
├─ jurisdictions/
│  ├─ us-federal/
│  │  ├─ statutes/ucmj/            # Uniform Code of Military Justice articles
│  │  ├─ manuals/mcm/              # Manual for Courts-Martial excerpts
│  │  ├─ jury_or_panel_instructions/
│  │  └─ foundational_guidance/
│  ├─ us-ca/
│  │  ├─ penal_code/sections/      # California Penal Code sections
│  │  ├─ jury_instructions/
│  │  └─ foundational_guidance/
│  └─ us-ny/
├─ shared/                         # cross-jurisdiction guidance
└─ schemas/                        # JSON Schemas for the content above
```

All content is keyed by jurisdiction directory. JSON documents validate
against the schemas in `schemas/`; markdown documents carry a JSON
frontmatter block (delimited by `---`) with identifying metadata.
