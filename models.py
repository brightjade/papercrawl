from dataclasses import asdict, dataclass, field
import json


@dataclass
class Paper:
    title: str
    link: str
    authors: list[str]
    selection: str = ""
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    citation_count: int | None = None
    forum_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != ""}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        return cls(
            title=data["title"],
            link=data.get("link", ""),
            authors=data.get("authors", []),
            keywords=data.get("keywords", []),
            abstract=data.get("abstract", ""),
            selection=data.get("selection", ""),
            citation_count=data.get("citation_count"),
            forum_id=data.get("forum_id", ""),
        )
