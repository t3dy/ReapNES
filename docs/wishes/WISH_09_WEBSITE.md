# WISH #9: Website Polish and Deployment

## 1. What This Wish Is

Bring the ReapNES Jekyll site (https://t3dy.github.io/ReapNES/) from
"content exists" to "a visitor can navigate and understand the project
in five minutes." The site has substantial content -- annotated source
code, a methodology paper, a research log, game-specific analyses, and
architecture docs -- but it lacks coherent navigation, consistent
cross-linking, and discoverability for pages that exist but are not
linked from anywhere.

## 2. Why It Matters

- The site is the public face of the project. GitHub visitors land on
  the README, which links to the site. If the site is hard to navigate,
  the documentation effort is wasted.
- The LLM methodology paper and annotated source code are genuinely
  novel contributions to the NES RE community. They deserve a clear
  path from the front page.
- Several dozen docs exist in the `docs/` directory but are not linked
  from `index.md` or any other page. They are invisible to visitors.
- The hacker theme has no built-in navigation sidebar or breadcrumbs.
  Without manual navigation structure, every page is a dead end.

## 3. Current State

### What is live and linked from index.md

The homepage (`index.md`) has four content sections with links:

**Explore section (2 links):**
- Annotated Source Code (`code/`) -- works, has its own index with 5 subpages
- LLM Methodology (`docs/LLM_METHODOLOGY`) -- works

**Architecture and Reference (5 links):**
- DRIVER_MODEL, GAME_MATRIX, COMMAND_MANIFEST, INVARIANTS, UNKNOWNS

**Workflow and Methodology (5 links):**
- TRACE_WORKFLOW, RESEARCH_LOG, MESENCAPTURE, HOWTOREADACAPTURE, HOWTOBEMOREFLEXIBLE

**Game-Specific (7 links):**
- CONTRAGOALLINE, CONTRACOMPARISON, CONTRALESSONSTOCV1, KONAMITAKEAWAY, CHECKLIST, NOTEDURATIONS, DONEBEFORE

**Process (2 links):**
- SWARMPERFORMED1, SWARMAGENTIDS

Total linked from homepage: ~21 docs + 5 code pages = 26 pages.

### What exists but is NOT linked from any navigation

At least 47 files in `docs/` have YAML frontmatter (so Jekyll will
build them as pages), but roughly half are not linked from `index.md`.
Notable unlinked pages include:

- `DRIVER_TAXONOMY.md` -- sound driver taxonomy across the NES library
- `ENVELOPE_SYSTEMS.md` -- envelope system comparison
- `POINTER_MODELS.md` -- pointer table format documentation
- `PERCUSSION_MODELS.md` -- percussion system comparison
- `HARDWARE_VARIANTS.md` -- NES hardware variant reference
- `FAILURE_MODES.md` -- failure mode catalog
- `NEW_ROM_WORKFLOW.md` -- workflow for adding a new ROM
- `FLEXIBLE_PARSER_ARCHITECTURE.md` -- parser architecture design doc
- `AUDIT_REPORT.md` -- extraction audit report
- `DRIVER_IDENTIFICATION.md` -- driver identification methodology
- `TRACE_VALIDATION_NOTES.md` -- trace validation notes
- `COMMAND_VARIABILITY.md` -- command set variability across games
- `VERSION4STORY.md`, `LATESTFIXES.md`, `OCTAVETOOLOWONPULSE.md` -- CV1 session narratives
- `CONTRAVERSIONS.md`, `CONTRALESSONS.md` -- Contra session narratives

Some of these (HANDOVER.md, MISTAKEBAKED.md, DECKARDCONTRASTAGE2.md,
CONTRACONTEXTENGINEERING.md) are internal project docs that probably
should NOT be on the public site, but are currently not excluded in
`_config.yml`.

### Jekyll configuration

- Theme: `jekyll-theme-hacker`
- Default layout set for `docs/` path via `_config.yml` defaults
- Exclusion list covers ROMs, traces, presets, CLAUDE.md, but does NOT
  exclude internal docs like HANDOVER.md or MISTAKEBAKED.md
- No `navigation.yml` or equivalent -- all nav is manual HTML/markdown
- No 404 page

### What is missing entirely

- No site-wide navigation bar or sidebar
- No table of contents on long pages
- No breadcrumbs ("Home > Docs > Driver Model")
- No "back to home" link on subpages (theme may provide this)
- No favicon or open graph metadata for social sharing
- No 404.md page
- No sitemap or RSS feed configuration

## 4. Concrete Steps

### Phase A: Triage and Exclude (1 hour)

1. Audit all 70+ docs. Classify each as: **public** (belongs on site),
   **internal** (should be excluded), or **redundant** (superseded by
   another doc).
2. Add internal docs to the `exclude:` list in `_config.yml`.
3. For any doc that is public but lacks `layout: default` in its
   frontmatter, add it. The `_config.yml` defaults handle docs/ path,
   but verify every file renders correctly.

### Phase B: Navigation Structure (2 hours)

4. Add a `_data/navigation.yml` file defining a site-wide nav
   structure with sections matching the homepage categories:
   - Getting Started / Overview
   - Architecture and Reference
   - Workflow and Methodology
   - Game-Specific
   - Annotated Source Code
   - Process and Methodology
5. Add a `_includes/navigation.html` partial that renders the nav
   data as a sidebar or top nav. The hacker theme supports includes.
6. Override the default layout to inject the navigation include.
7. Add a "Back to Home" link to every page (if the theme does not
   already provide one).

### Phase C: Cross-Linking and TOC (2 hours)

8. Add the newly-public unlinked docs to `index.md` in the
   appropriate section tables.
9. Add a new section to `index.md` for the taxonomy/reference docs
   (DRIVER_TAXONOMY, ENVELOPE_SYSTEMS, POINTER_MODELS, etc.).
10. Add `{:toc}` kramdown table of contents to long pages (any page
    over ~200 lines). Kramdown supports this natively.
11. Add cross-links between related pages:
    - DRIVER_MODEL should link to GAME_MATRIX and COMMAND_MANIFEST
    - TRACE_WORKFLOW should link to MESENCAPTURE and HOWTOREADACAPTURE
    - CONTRAGOALLINE should link to CONTRACOMPARISON and CONTRALESSONSTOCV1
    - Each code/ page should link to its corresponding docs/ page
12. Add "See also" footers to pages with related content.

### Phase D: Polish (1 hour)

13. Create a `404.md` page with a link back to the homepage.
14. Add `jekyll-seo-tag` and `jekyll-sitemap` plugins to `_config.yml`
    (both are supported by GitHub Pages).
15. Add Open Graph metadata (title, description, image) for social
    sharing.
16. Verify all links work by running `htmlproofer` or manually
    clicking through the site.
17. Add a brief "About" section or page explaining the project scope
    and author.

### Phase E: README Alignment (30 min)

18. Ensure README.md and index.md tell a consistent story. Currently
    they are close but not identical -- the README has a project
    structure section and requirements that the site homepage lacks.
19. Add a "Requirements" or "Quick Start" section to index.md, or
    link to a dedicated page.

## 5. Estimated Effort

| Phase | Hours | Notes |
|-------|-------|-------|
| A: Triage and exclude | 1 | Mostly reading frontmatter, editing _config.yml |
| B: Navigation structure | 2 | Requires Jekyll layout override, YAML data file |
| C: Cross-linking and TOC | 2 | Editing 20+ files, adding links and TOC markers |
| D: Polish | 1 | 404, SEO, link verification |
| E: README alignment | 0.5 | Minor edits to two files |
| **Total** | **6.5** | Can be done in 2-3 sessions |

## 6. Dependencies

- **None blocking.** The site is already deployed and the theme works.
- Jekyll `hacker` theme must support layout overrides for nav to work.
  If it does not, the fallback is adding nav HTML directly to each page
  (more tedious but no dependency).
- `jekyll-seo-tag` and `jekyll-sitemap` are available on GitHub Pages
  but must be added to `_config.yml` plugins list.
- No dependency on extraction pipeline, parser code, or trace tooling.

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Internal docs (HANDOVER, MISTAKEBAKED) are already indexed by search engines | Medium | Low -- no secrets, just noisy | Add to exclude list promptly |
| Hacker theme does not support custom includes/layouts | Low | Medium -- nav requires more manual work | Test layout override first; fall back to inline nav |
| Broken links after restructuring | Medium | Low | Run link checker after changes |
| Scope creep into content rewriting | High | Medium -- time sink | Limit to navigation and linking only; content quality is a separate wish |
| Doc triage disagreements (public vs internal) | Low | Low | When in doubt, exclude; can always add back |

## 8. Success Criteria

1. Every public doc is reachable within 2 clicks from the homepage.
2. No internal-only docs (HANDOVER, MISTAKEBAKED, DECKARDCONTRASTAGE2,
   CONTRACONTEXTENGINEERING) are served by the site.
3. Every page has a way to navigate back to the homepage.
4. Long pages (200+ lines) have a table of contents.
5. Link checker reports zero broken internal links.
6. README.md and index.md present consistent information.
7. The site has a 404 page, sitemap, and basic SEO metadata.

## 9. Priority Ranking

**Priority: Medium.** The site is already live and functional. The
content is the hard part and it already exists. This wish is about
making that content findable and navigable -- important for community
engagement and credibility, but not blocking any extraction or pipeline
work. It should be done before any public announcement or community
outreach, but can wait behind active extraction work (Contra envelopes,
new game support).

Recommended sequencing: after Contra reaches a stable state, before
any attempt to attract outside contributors.
