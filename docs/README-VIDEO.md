# Publishing the README walkthrough

The root README reserves a `Video walkthrough` section outside all generated download
blocks. Release automation preserves it.

1. Export a short MP4 using H.264. Include readable captions and avoid exposing tokens,
   pairing codes, personal chats or account details in the recording.
2. In GitHub's web interface, upload the video as an attachment in the repository's
   editor or a draft issue/PR comment. Wait for the upload to finish and copy the
   generated `https://github.com/user-attachments/assets/...` URL.
3. Put that URL on its own line, with blank lines around it, between `arise-video:start`
   and `arise-video:end` in `README.md`. Replace the “video is being prepared” sentence
   with a brief description of what the viewer will learn. Do not put the URL inside
   a code fence or use image syntax for an MP4.
4. Preview the README on GitHub and verify playback on desktop and mobile. Include
   a normal “Open video” link as a fallback. Rendering and codec support can vary.
5. Commit the README on `main`; the QA mirror receives the same documentation.

GitHub currently lists video upload limits of 10 MB for free-plan repositories and
100 MB for paid-plan repositories, subject to uploader eligibility. A YouTube link
is an alternative for a long tutorial, but use a linked thumbnail rather than
promising an inline YouTube player in a GitHub README. Keep large recordings out
of Git history.

Sources:

- [GitHub: attaching files, formats, codecs and size limits](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
- [GitHub community: bare attachment URL playback](https://github.com/orgs/community/discussions/209976)

The placeholder does not claim a video has already been uploaded or tested.
