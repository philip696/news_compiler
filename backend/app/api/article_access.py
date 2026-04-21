"""Whether an article id may receive feed-style interactions (like / bookmark)."""

from __future__ import annotations

from .. import state
from ..db.app_repository import AppRepository


def article_id_allowed_for_user_actions(
    repo: AppRepository, user_id: int, article_id: str
) -> bool:
    if article_id in state.articles:
        return True
    return repo.weread_article_belongs_to_user(user_id, article_id)


def hydrate_saved_article_rows(
    repo: AppRepository, user_id: int, article_ids: list[str]
) -> list[dict]:
    """Resolve bookmark/like id lists to article dicts (main feed + WeRead)."""
    result: list[dict] = []
    missing: list[str] = []
    for aid in article_ids:
        row = state.articles.get(aid)
        if row:
            result.append(row)
        else:
            missing.append(aid)
    if missing:
        weread = repo.weread_articles_as_feed_dicts(user_id, frozenset(missing))
        for aid in missing:
            w = weread.get(aid)
            if w:
                result.append(w)
    return result
