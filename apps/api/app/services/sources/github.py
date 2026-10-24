import hashlib
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings
from app.schemas.source import NormalizedSource, SourceEvidence
from app.services.sources.base import RawSource, stable_source_id
from app.services.sources.errors import SourceError


@dataclass(frozen=True, slots=True)
class GitHubTarget:
    owner: str
    repository: str
    kind: str = "repository"
    number: int | None = None
    path: str | None = None
    ref: str | None = None

    @property
    def canonical_url(self) -> str:
        base = f"https://github.com/{self.owner}/{self.repository}"
        if self.kind == "issue":
            return f"{base}/issues/{self.number}"
        if self.kind == "pull_request":
            return f"{base}/pull/{self.number}"
        if self.kind == "file":
            return f"{base}/blob/{self.ref}/{self.path}"
        return base


def parse_github_target(url: str) -> GitHubTarget:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if (parsed.hostname or "").casefold().removeprefix("www.") != "github.com" or len(parts) < 2:
        raise SourceError("INVALID_URL", "GitHub URL must identify an owner and repository")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    if len(parts) >= 4 and parts[2] == "issues" and parts[3].isdigit():
        return GitHubTarget(owner, repository, "issue", number=int(parts[3]))
    if len(parts) >= 4 and parts[2] == "pull" and parts[3].isdigit():
        return GitHubTarget(owner, repository, "pull_request", number=int(parts[3]))
    if len(parts) >= 5 and parts[2] in {"blob", "raw"}:
        return GitHubTarget(
            owner,
            repository,
            "file",
            path="/".join(parts[4:]),
            ref=parts[3],
        )
    return GitHubTarget(owner, repository)


class GitHubSourceAdapter:
    source_type = "github"

    def can_handle(self, url: str) -> bool:
        return (urlparse(url).hostname or "").casefold().removeprefix("www.") == "github.com"

    def _request(
        self, client: httpx.Client, path: str, accept: str = "application/vnd.github+json"
    ) -> httpx.Response:
        try:
            response = client.get(path, headers={"Accept": accept})
        except httpx.TimeoutException as exc:
            raise SourceError(
                "FETCH_TIMEOUT", "GitHub did not respond before the timeout", retryable=True
            ) from exc
        except httpx.RequestError as exc:
            raise SourceError(
                "FETCH_FAILED", "GitHub could not be reached", retryable=True
            ) from exc
        if response.status_code == 404:
            return response
        if response.status_code in {401, 403}:
            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining == "0":
                raise SourceError(
                    "RATE_LIMITED",
                    "GitHub API rate limit reached; configure GITHUB_TOKEN or retry later",
                    retryable=True,
                    status_code=response.status_code,
                )
            code = "AUTH_REQUIRED" if response.status_code == 401 else "ACCESS_DENIED"
            raise SourceError(
                code,
                "GitHub resource is private or access was denied",
                status_code=response.status_code,
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise SourceError(
                "RATE_LIMITED" if response.status_code == 429 else "FETCH_FAILED",
                "GitHub API is temporarily unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise SourceError(
                "FETCH_FAILED",
                f"GitHub API returned HTTP {response.status_code}",
                status_code=response.status_code,
            )
        return response

    def fetch(self, url: str) -> RawSource:
        target = parse_github_target(url)
        api_base = "https://api.github.com"
        repo_path = f"/repos/{quote(target.owner)}/{quote(target.repository)}"
        headers = {"User-Agent": "ResearchSystem/1.0", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token.get_secret_value()}"
        metadata: dict[str, object] = {"target": target}
        content = ""
        with httpx.Client(
            base_url=api_base, headers=headers, timeout=settings.intake_request_timeout_seconds
        ) as client:
            repository_response = self._request(client, repo_path)
            if repository_response.status_code == 404:
                raise SourceError(
                    "SOURCE_NOT_FOUND", "GitHub repository was not found or is private"
                )
            repository_data = repository_response.json()
            metadata["repository"] = repository_data

            if target.kind == "file":
                response = self._request(
                    client,
                    f"{repo_path}/contents/{quote(target.path or '', safe='/')}"
                    f"?ref={quote(target.ref or '')}",
                    "application/vnd.github.raw+json",
                )
                if response.status_code == 404:
                    raise SourceError("SOURCE_NOT_FOUND", "GitHub file was not found")
                if len(response.content) > settings.intake_max_content_bytes:
                    raise SourceError(
                        "CONTENT_TOO_LARGE",
                        "GitHub file exceeds the configured size limit",
                        details={"limit_bytes": settings.intake_max_content_bytes},
                    )
                content = response.text
                metadata["file_size"] = len(response.content)
            elif target.kind in {"issue", "pull_request"}:
                endpoint = "issues" if target.kind == "issue" else "pulls"
                response = self._request(client, f"{repo_path}/{endpoint}/{target.number}")
                if response.status_code == 404:
                    raise SourceError(
                        "SOURCE_NOT_FOUND", f"GitHub {target.kind.replace('_', ' ')} was not found"
                    )
                item = response.json()
                comments = self._request(
                    client, f"{repo_path}/issues/{target.number}/comments?per_page=20"
                )
                comment_data = comments.json() if comments.status_code == 200 else []
                metadata["item"] = item
                metadata["comments"] = comment_data
                content = "\n\n".join(
                    [item.get("body") or ""]
                    + [comment.get("body") or "" for comment in comment_data]
                )
            else:
                readme_response = self._request(
                    client, f"{repo_path}/readme", "application/vnd.github.raw+json"
                )
                readme = readme_response.text if readme_response.status_code == 200 else ""
                languages_response = self._request(client, f"{repo_path}/languages")
                tree_response = self._request(
                    client,
                    f"{repo_path}/git/trees/"
                    f"{quote(repository_data.get('default_branch') or 'HEAD')}?recursive=1",
                )
                tree = (
                    tree_response.json().get("tree", []) if tree_response.status_code == 200 else []
                )
                bounded_tree = [
                    {"path": item.get("path"), "type": item.get("type"), "size": item.get("size")}
                    for item in tree[:200]
                    if item.get("path") and str(item.get("path")).count("/") <= 3
                ][:100]
                metadata["readme"] = readme
                metadata["languages"] = (
                    languages_response.json() if languages_response.status_code == 200 else {}
                )
                metadata["tree"] = bounded_tree
                metadata["tree_truncated"] = len(tree) > len(bounded_tree)
                content = readme

        return RawSource(
            requested_url=url,
            final_url=target.canonical_url,
            content_type="application/vnd.github+json",
            content=content.encode(),
            metadata=metadata,
        )

    def extract(self, source: RawSource) -> NormalizedSource:
        target = source.metadata["target"]
        if not isinstance(target, GitHubTarget):
            raise SourceError("EXTRACTION_FAILED", "GitHub target metadata is invalid")
        repository = source.metadata.get("repository")
        if not isinstance(repository, dict):
            raise SourceError("EXTRACTION_FAILED", "GitHub repository metadata is invalid")
        raw_text = source.content.decode(errors="replace").strip()
        title = repository.get("full_name") or f"{target.owner}/{target.repository}"
        summary = repository.get("description") or ""
        metadata: dict[str, object] = {
            "resource_kind": target.kind,
            "description": repository.get("description"),
            "topics": repository.get("topics", []),
            "primary_language": repository.get("language"),
            "languages": source.metadata.get("languages", {}),
            "license": (repository.get("license") or {}).get("spdx_id"),
            "stars": repository.get("stargazers_count"),
            "default_branch": repository.get("default_branch"),
            "tree": source.metadata.get("tree", []),
            "tree_truncated": source.metadata.get("tree_truncated", False),
        }
        if target.kind in {"issue", "pull_request"}:
            item = source.metadata.get("item")
            if not isinstance(item, dict):
                raise SourceError("EXTRACTION_FAILED", "GitHub issue metadata is invalid")
            title = item.get("title") or title
            summary = item.get("body") or ""
            metadata.update(
                {
                    "number": target.number,
                    "state": item.get("state"),
                    "labels": [label.get("name") for label in item.get("labels", [])],
                    "comments_count": item.get("comments", 0),
                    "merged": item.get("merged") if target.kind == "pull_request" else None,
                }
            )
        elif target.kind == "file":
            title = f"{target.repository}/{target.path}"
            summary = f"File from {target.owner}/{target.repository} at {target.ref}"
            metadata.update(
                {
                    "path": target.path,
                    "ref": target.ref,
                    "size_bytes": source.metadata.get("file_size"),
                }
            )
        elif not raw_text:
            raw_text = summary

        source_id = stable_source_id(self.source_type, target.canonical_url)
        evidence = [
            SourceEvidence(
                id=f"{source_id}:evidence:{index}",
                text=paragraph[:800],
                section=target.kind.replace("_", " ").title(),
                location=f"paragraph:{index + 1}",
            )
            for index, paragraph in enumerate(
                part.strip() for part in raw_text.split("\n\n") if len(part.strip()) >= 30
            )
        ][:12]
        created_at = repository.get("created_at")
        published_at = (
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if isinstance(created_at, str)
            else None
        )
        owner = repository.get("owner") or {}
        metadata["content_hash"] = hashlib.sha256(raw_text.encode()).hexdigest()
        return NormalizedSource(
            id=source_id,
            source_type=self.source_type,
            canonical_url=target.canonical_url,
            title=str(title),
            authors=[owner.get("login")] if owner.get("login") else [],
            published_at=published_at,
            description=str(summary)[:1000],
            raw_text=raw_text,
            summary=str(summary)[:2000],
            language="en",
            metadata=metadata,
            evidence=evidence,
        )

    def collect(self, url: str) -> NormalizedSource:
        return self.extract(self.fetch(url))
