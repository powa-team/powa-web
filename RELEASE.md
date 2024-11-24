## Releasing a new version of PoWA-web

- [ ] Ensure there's no blocker issues and pull requests are resolved.
- [ ] Bump the powa-web `__VERSION__` in `powa/__init__.py`.
- [ ] Make sure CI runs successfully.
- [ ] Build and commit assets:
  - [ ] Run `npm ci` to install packages.
  - [ ] Run `npm run build` to build assets (JS and CSS).
- [ ] Update [the changelog](https://github.com/powa-team/powa-web/blob/master/CHANGELOG) if not already up-to-date.
- [ ] Commit the changes (files in `powa/static/dist`, `powa/__init__.py` and `CHANGELOG`).
- [ ] Create a tag either from the command line or Github web interface.
- [ ] Verify that images are pushed to Docker hub (via the powa-podman repo).
- [ ] Publish to `pypi`.
