# Reviewed software release and citation handoff

The repository now supplies CITATION.cff for GitHub's software citation feature.
It uses the collective name "Gluco contributors" and links the contributor record.
Before a release, the team must approve whether to retain that collective credit
or replace it with each contributor's preferred name and author order. No ORCID,
affiliation, release number, release date or DOI has been invented.

## Prepare the exact submission

1. Agree authorship, title, description and the existing repository license.
   Do not confuse source-dataset citations with the Gluco software citation.
2. Merge reviewed fixes, choose the exact submission commit and verify its
   main CI results. Record that SHA and the review in issue #175.
3. Inspect the tracked release contents for credentials, restricted data,
   temporary state and recordings containing sensitive information. Generated
   public documentation and dependency inventories are part of the software.
4. Choose the release tag/version together. Add the actual version and release
   date to CITATION.cff only once decided; validate it again. A citation file
   does not create a release or reserve a DOI.

## Archive through the authorized account

The repository owner connects the repository to their authorized Zenodo/GitHub
integration. Follow [Zenodo's archive procedure](https://help.zenodo.org/docs/github/archive-software/github-upload/).
Create the reviewed GitHub release from the agreed exact commit only after
metadata is approved. Do not publish a release merely to fill a rubric row.
Check import success, creators, software resource type, license, actual archived
files, tag/commit and metadata on the record before declaring the archive done.

Zenodo can use CITATION.cff metadata on a best-effort basis. If .zenodo.json is
added later, that file takes precedence; keep the two descriptions consistent.
See the [official metadata FAQ](https://support.zenodo.org/help/en-gb/24-github-integration/96-how-does-a-citation-cff-file-affect-metadata-of-my-github-release).
No Zenodo account connection, metadata submission, archive or release is created
by this repository change.

## Verify the result and finish #175

- Confirm the resolved DOI identifies Gluco software rather than a dataset.
- Record the version DOI for the submitted artifact and distinguish it from a
  concept DOI covering all versions, if provided by the archive.
- Add only the real returned DOI to citation metadata and a clickable README
  badge. Verify it opens the correct record from an unauthenticated browser.
- Link the release, archive, exact SHA, agreed creator list and second-person
  check in #175 before completing its acceptance criteria.

Until then, cite the repository with the exact commit used. The README must not
display an invented DOI or imply that an archive already exists.

## Validate citation metadata

```sh
uv run --python 3.12 --no-project --with cffconvert==2.0.0 \
  cffconvert --validate --infile CITATION.cff
```

The citation-metadata CI job runs this schema check. It checks file validity,
not human authorship approval, DOI resolution or an archive's existence.
