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
    influential_citation_count: int | None = None
    reference_count: int | None = None
    tldr: str = ""
    publication_date: str = ""
    fields_of_study: list[str] = field(default_factory=list)
    open_access_pdf: str = ""
    external_ids: dict = field(default_factory=dict)
    match_status: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}

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
            influential_citation_count=data.get("influential_citation_count"),
            reference_count=data.get("reference_count"),
            tldr=data.get("tldr", ""),
            publication_date=data.get("publication_date", ""),
            fields_of_study=data.get("fields_of_study", []),
            open_access_pdf=data.get("open_access_pdf", ""),
            external_ids=data.get("external_ids", {}),
            match_status=data.get("match_status", ""),
        )
