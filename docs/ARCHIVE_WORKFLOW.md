# Archive Work Workflow

This workflow reduces the size of image requests without changing the archive's
visual language or source files. The full analysis rules remain in
`docs/IMAGE_ANALYSIS_SPEC.md`.

## One round, three images, one conversation

1. Select exactly three candidate images.
2. Run `python3 scripts/archive_work.py prepare <image> [<image> ...]`.
3. Call the image viewer once for each returned file under `archive-work/vision/`,
   one image at a time. Never open the original large file for routine analysis.
   For a screenshot with bars or interface chrome, use `archive_work.py crop`,
   then view the cropped result once to verify that only the photo/illustration remains.
4. After each image, write the complete structured analysis to a separate file
   under `archive-work/analyses/`. Mark it with:

   ```sh
   python3 scripts/archive_work.py mark <sha256> \
     --status analysis_saved \
     --analysis archive-work/analyses/<name>.json
   ```

5. Complete the same conversation with the other two images. The compressed
   working copies keep the cumulative image payload small, so a new chat per
   image is unnecessary.
6. Merge the three saved analyses only after analysis is complete. Use
   `python3 scripts/archive_work.py summary` to recover the exact state when a
   conversation must be resumed.

`archive-work/` is local working state and is ignored by Git. Original images
under the candidate folder and `images/` are never modified.

## Status values

- `prepared`: compressed working copy exists.
- `analyzing`: analysis is in progress.
- `analysis_saved`: complete structured draft is stored on disk.
- `imported`: the draft has been merged into the archive.
- `skipped`: deliberately not archived, such as a photo of the user.
- `rejected`: failed or unsuitable source.

## Duplicate hints

Run the archive fingerprint index once, then refresh it after an import:

```sh
python3 scripts/archive_work.py seed-archive
python3 scripts/archive_work.py prepare <candidate>
```

An exact SHA-256 match is conclusive. A perceptual hint is only a warning;
still follow the content-cropping comparison required by `AGENTS.md` before
deciding that a candidate is a duplicate.
