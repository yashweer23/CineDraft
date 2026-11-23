# Phase 4 source references

Official TMDB documentation consulted on 21 October 2026. The implementation uses these read endpoints and application credentials; game scope thresholds and credit eligibility remain CineDraft policy.

- [Application authentication](https://developer.themoviedb.org/docs/authentication-application): API Read Access Token in a bearer header.
- [Movie details](https://developer.themoviedb.org/reference/movie-details), [credits](https://developer.themoviedb.org/reference/movie-credits), [keywords](https://developer.themoviedb.org/reference/movie-keywords).
- [Append to response](https://developer.themoviedb.org/docs/append-to-response): related movie resources in one request.
- [Movie discovery](https://developer.themoviedb.org/reference/discover-movie): source selection, pages and filters.
- [Configuration](https://developer.themoviedb.org/reference/configuration-details) and [image basics](https://developer.themoviedb.org/docs/image-basics): supported image bases/sizes and source paths.
- [Rate limiting](https://developer.themoviedb.org/docs/rate-limiting): handle 429 and changing provider limits.
- [FAQ](https://developer.themoviedb.org/docs/faq): API access and attribution requirements.
- [Logo and attribution page](https://www.themoviedb.org/about/logos-attribution): official branding reference; this page could not be fully retrieved in the delivery environment. Verify locally before public distribution.

See earlier [Phase 3 references](../phase-03/references.md) for database/versioning foundations. The package does not include a commercial license determination; follow the provider's terms for your intended use.
