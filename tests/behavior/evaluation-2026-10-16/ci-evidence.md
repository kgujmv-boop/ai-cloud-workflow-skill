# Automated code checks

The workflow uses read-only repository contents, pinned official actions, and a standard Ubuntu public-repository runner. It does not request secrets, upload artifacts, use paid larger runners, or test cloud accounts. A job guard skips private copies.

- Actual GitHub Actions run: https://github.com/kgujmv-boop/ai-cloud-workflow-skill/actions/runs/38848576178
- Commit: `329b6fcb5d2038310c810f5d5f589344d959b682`
- Observed on 2026-10-16: successful, 12 seconds (GitHub run summary).
- Checks: 28 manifest unit tests; 16 CPU checkpoint/recovery checks.
- Final demo output SHA-256: `480d53766e520a3cd3a7072228a9c21c8a91af2cd31f617b13db163da1fe78c2`.

This is evidence of an actual hosted code-test run. It is separate from the four-case plan comparison and does not prove external GPU scheduling, provider login, or cloud backup recovery.

Pinned official action sources, checked 2026-10-16:

- [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1), commit `3d3c42e5aac5ba805825da76410c181273ba90b1`, Node 24.
- [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0), commit `5fda3b95a4ea91299a34e894583c3862153e4b97`, Node 24.
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): standard hosted runners for public repositories are free; larger runners have different billing.
