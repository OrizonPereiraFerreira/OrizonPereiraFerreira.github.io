# OrizonPereiraFerreira.github.io

Source of the academic page of Orizon P. Ferreira: https://orizonpereiraferreira.github.io

Plain HTML, CSS and JavaScript. To add a paper, a repository or a student, edit `js/data.js`.

## Automatic publication updates

Every Monday the workflow `.github/workflows/sync-publications.yml` runs
`scripts/sync_publications.py`, which looks up the articles linked to ORCID 0000-0002-5758-0320
on [OpenAlex](https://openalex.org) (Google Scholar has no open API). When it finds a journal
article that is not on the page, or volume and pages for an item marked "To appear", it opens a
pull request; GitHub emails a notice, and the page changes only after the pull request is merged.

- Run it now: Actions tab > "Sync publications" > "Run workflow", or `gh workflow run sync-publications.yml`.
- Run it locally: `python3 scripts/sync_publications.py --dry-run` (shows what would change).
- Never add a given article: put its DOI in `scripts/sync-ignore.txt`.
