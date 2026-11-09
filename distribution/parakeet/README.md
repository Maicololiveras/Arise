# ARISE dictation model distribution

Distribution branch: `distribution/parakeet-v3`.
Pinned release: `voice-parakeet-v3-2bda32ec70b0`.

Model/runtime binaries are release assets, not large files in Git history or Git
LFS. This directory records upstream sources, checksums and reproducible publishing.
Actions downloads the pinned Hugging Face/npm originals, verifies all 11 files,
stages a draft release and downloads uploaded assets again to verify checksums
before publishing. Existing published releases are immutable: changed bytes need
a new version and reviewed hashes.

Clients download only from GitHub Releases, with constrained HTTPS redirects.
Proxies must allow GitHub and `release-assets.githubusercontent.com`. This does
not bypass a GitHub block or justify disabling TLS. Licenses/attribution remain
in NOTICE.txt. Bytes are not converted or recompressed. The model is about 670 MB;
the 11 assets across supported targets total 733348427 bytes.

The mirrored dictation target matrix is separate from ARISE's native application
matrix. In particular, the pinned Windows dictation runtime does not support
Windows ARM64. See [dictation](../../docs/DICTATION-PARAKEET-QA.md) and
[native previews](../../docs/NATIVE-DISTRIBUTIONS.md).
