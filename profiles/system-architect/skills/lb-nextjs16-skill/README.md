# Next.js 16 Documentation Skill

Complete Next.js 16.2.0-canary.30 documentation packaged as an OpenClaw AgentSkill.

## Contents

- **App Router** (modern Next.js with React Server Components)
- **Pages Router** (legacy architecture, still supported)
- **API Reference** (complete API docs for all features)
- **Migration Guides** (from Vite, CRA, Pages → App Router)
- **Upgrade Guides** (v14, v15, v16)

## Structure

```
references/
├── 01-app/           # App Router documentation
├── 02-pages/         # Pages Router documentation
├── 03-architecture/  # Compiler, Fast Refresh, etc.
└── 04-community/     # Contribution guide, Rspack
```

## Installation

Via ClawHub:
```bash
clawhub install lb-nextjs16-skill
```

Or manually: Download and extract into your OpenClaw workspace `skills/` folder.

## Usage

This skill triggers automatically when you ask questions about Next.js features, configuration, routing, data fetching, deployment, or migration.

## Source

Documentation extracted from [vercel/next.js](https://github.com/vercel/next.js) `canary` branch (v16.2.0-canary.30).

## License

Documentation content: MIT (from Next.js project)
