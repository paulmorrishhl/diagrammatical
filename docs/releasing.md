# Release and local development

The intended first release is `0.1.0`, matching the plugin, marketplace and package manifests.
Follow `RELEASE_CHECKLIST.md`; do not update screenshots automatically in CI. Local acceptance must
install from the local marketplace rather than relying only on `--plugin-dir`.

No release command in this repository pushes, tags, publishes or creates a GitHub release. Those
external actions require explicit maintainer authorisation after every required v1 audit item passes.
