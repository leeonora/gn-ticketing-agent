from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from pydantic_ai import UsageLimits

from scripts.analyze_pr import (
    analyze_diff,
    get_pr_diff,
    post_pr_comment,
)


def test_get_pr_diff():
    """The reviewer retrieves the correct PR diff."""
    expected_diff = "diff --git a/example.py b/example.py\n+print('Hello world')\n"

    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/repos/owner/repo/pulls/42"
        assert request.headers["Accept"] == "application/vnd.github.diff"
        return httpx.Response(200, text=expected_diff)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = get_pr_diff(client, "owner/repo", 42)

    assert result == expected_diff


def test_get_pr_diff_http_error():
    """GitHub API errors are not silently ignored."""

    def handler(request):
        return httpx.Response(404, json={"message": "Not Found"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.HTTPStatusError) as exc_info,
    ):
        get_pr_diff(client, "owner/repo", 999)

    assert exc_info.value.response.status_code == 404


def test_analyze_diff():
    """The diff is sent to the reviewer and feedback is returned."""
    reviewer = Mock()
    reviewer.run_sync.return_value = SimpleNamespace(
        output="The changes look good, but add error handling."
    )

    diff = "+print('Hello world')"
    result = analyze_diff(reviewer, diff)

    assert result == ("The changes look good, but add error handling.")

    reviewer.run_sync.assert_called_once()

    args, kwargs = reviewer.run_sync.call_args

    assert diff in args[0]
    assert isinstance(kwargs["usage_limits"], UsageLimits)
    assert kwargs["usage_limits"].request_limit == 1


def test_analyze_empty_diff():
    """An empty diff must not trigger an LLM request."""
    reviewer = Mock()

    with pytest.raises(ValueError, match="diff is empty"):
        analyze_diff(reviewer, "   ")

    reviewer.run_sync.assert_not_called()


def test_analyze_empty_response():
    """An empty LLM response must not be published."""
    reviewer = Mock()
    reviewer.run_sync.return_value = SimpleNamespace(output="")

    with pytest.raises(ValueError, match="empty review"):
        analyze_diff(reviewer, "+new code")


def test_post_pr_comment():
    """Exactly one comment is posted to the correct PR."""
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json={"id": 123})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        post_pr_comment(
            client,
            "owner/repo",
            42,
            "Consider adding input validation.",
        )

    assert len(requests) == 1

    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == ("/repos/owner/repo/issues/42/comments")

    import json

    body = json.loads(request.content)

    assert body["body"] == (
        "## Automated PR Review\n\nConsider adding input validation."
    )


def test_post_pr_comment_http_error():
    """A failed comment request raises an HTTP error."""

    def handler(request):
        return httpx.Response(403, json={"message": "Forbidden"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.HTTPStatusError) as exc_info,
    ):
        post_pr_comment(client, "owner/repo", 42, "Review")

    assert exc_info.value.response.status_code == 403
