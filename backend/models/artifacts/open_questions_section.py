from dataclasses import dataclass, field


@dataclass
class OpenQuestionsSection:
    questions: list[str] = field(
        default_factory=list
    )
