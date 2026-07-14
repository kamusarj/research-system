import hashlib
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.source import NormalizedSource, SourceEvidence
from app.services.sources.base import stable_source_id


class GitHubSourceAdapter:
    source_type = "github"

    def _request(
        self, client: httpx.Client, path: str, accept: str = "application/json"
    ) -> httpx.Response:
        response = client.get(path, headers={"Accept": accept})
        if response.status_code == 404:
            return response
        if response.status_code in {401, 403}:
            remaining = response.headers.get("x-ratelimit-remaining")
            message = (
                "GitHub API rate limit reached"
                if remaining == "0"
                else "GitHub repository is private or access was denied"
            )
            raise HTTPException(response.status_code, message)
        response.raise_for_status()
        return response

    def collect(self, url: str) -> NormalizedSource:
        parts = [part for part in urlparse(url).path.split("/") if part]
        if len(parts) < 2:
            raise HTTPException(422, "GitHub URL must identify an owner and repository")
        owner, repository = parts[0], parts[1].removesuffix(".git")
        canonical = f"https://github.com/{owner}/{repository}"
        api_base = f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
        headers = {"User-Agent": "ResearchSystemBot/1.0"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token.get_secret_value()}"

        with httpx.Client(base_url=api_base, headers=headers, timeout=30) as client:
            metadata_response = self._request(client, "")
            if metadata_response.status_code == 404:
                raise HTTPException(404, "GitHub repository was not found or is private")
            repository_data = metadata_response.json()

            readme_response = self._request(
                client, "/readme", "application/vnd.github.raw+json"
            )
            readme = readme_response.text if readme_response.status_code == 200 else ""

            languages_response = self._request(client, "/languages")
            languages = languages_response.json() if languages_response.status_code == 200 else {}

            releases_response = self._request(client, "/releases?per_page=5")
            releases = releases_response.json() if releases_response.status_code == 200 else []

            manifests: dict[str, str] = {}
            for filename in ("package.json", "pyproject.toml", "requirements.txt"):
                response = self._request(
                    client,
                    f"/contents/{filename}",
                    "application/vnd.github.raw+json",
                )
                if response.status_code == 200:
                    manifests[filename] = response.text[:50_000]

            important_paths: list[dict[str, str]] = []
            for directory in ("docs", "examples"):
                response = self._request(client, f"/contents/{directory}")
                if response.status_code == 200 and isinstance(response.json(), list):
                    important_paths.extend(
                        {
                            "path": item.get("path", ""),
                            "url": item.get("html_url", ""),
                        }
                        for item in response.json()[:20]
                        if item.get("type") in {"file", "dir"}
                    )

        release_lines = []
        for release in releases:
            name = release.get("name") or release.get("tag_name")
            published = release.get("published_at") or "unknown date"
            release_lines.append(f"- {name} ({published})")
        sections = [
            f"# {repository_data.get('full_name', f'{owner}/{repository}')}",
            repository_data.get("description") or "",
            "## README\n" + readme,
            "## Releases\n" + "\n".join(release_lines),
        ]
        sections.extend(f"## {name}\n{content}" for name, content in manifests.items())
        raw_text = "\n\n".join(section for section in sections if section.strip())
        source_id = stable_source_id(self.source_type, canonical)
        evidence = [
            SourceEvidence(
                id=f"{source_id}:readme:{index}",
                text=paragraph[:800],
                section="README",
                location=f"readme:paragraph:{index + 1}",
            )
            for index, paragraph in enumerate(
                part.strip() for part in readme.split("\n\n") if len(part.strip()) >= 40
            )
        ][:10]
        published_at = None
        if repository_data.get("created_at"):
            published_at = datetime.fromisoformat(
                repository_data["created_at"].replace("Z", "+00:00")
            )
        owner_data = repository_data.get("owner") or {}
        return NormalizedSource(
            id=source_id,
            source_type=self.source_type,
            canonical_url=canonical,
            title=repository_data.get("full_name") or f"{owner}/{repository}",
            authors=[owner_data.get("login")] if owner_data.get("login") else [],
            published_at=published_at,
            raw_text=raw_text,
            summary=repository_data.get("description") or "",
            language="en",
            metadata={
                "description": repository_data.get("description"),
                "topics": repository_data.get("topics", []),
                "primary_language": repository_data.get("language"),
                "languages": languages,
                "license": (repository_data.get("license") or {}).get("spdx_id"),
                "stars": repository_data.get("stargazers_count"),
                "default_branch": repository_data.get("default_branch"),
                "releases": [
                    {
                        "tag": release.get("tag_name"),
                        "name": release.get("name"),
                        "published_at": release.get("published_at"),
                        "url": release.get("html_url"),
                    }
                    for release in releases
                ],
                "manifests": sorted(manifests),
                "important_paths": important_paths,
                "content_hash": hashlib.sha256(raw_text.encode()).hexdigest(),
            },
            evidence=evidence,
        )
