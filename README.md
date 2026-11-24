# OrizonPereiraFerreira.github.io

Source of the academic page of Orizon P. Ferreira: https://orizonpereiraferreira.github.io

Plain HTML, CSS and JavaScript. To add a paper, a repository or a student, edit `js/data.js`.

## Automatic publication updates

Every Monday the workflow `.github/workflows/sync-publications.yml` runs
`scripts/sync_publications.py`, which looks up the works linked to ORCID 0000-0002-5758-0320
on [OpenAlex](https://openalex.org) (Google Scholar has no open API) and the author's preprints on arXiv.
It proposes, as a pull request (GitHub emails a notice; the page changes only after the merge):

- new arXiv preprints (last 3 years) that are not on the page and not yet published;
- moving a preprint to "Articles in journals" once it is published, keeping its code/PDF links
  (recognised by its arXiv link on OpenAlex, even if the title changed);
- journal articles missing from the page, and volume/pages for items marked "To appear".

Closing a sync pull request without merging means its items are never proposed again.

- Run it now: Actions tab > "Sync publications" > "Run workflow", or `gh workflow run sync-publications.yml`.
- Run it locally: `python3 scripts/sync_publications.py --dry-run` (shows what would change).
- Never add a given item: put its DOI or arXiv id in `scripts/sync-ignore.txt`.
