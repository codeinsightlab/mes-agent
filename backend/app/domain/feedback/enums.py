from enum import IntEnum


class FeedbackType(IntEnum):
    LIKE = 1
    DISLIKE = 2

    @property
    def label(self) -> str:
        return {
            FeedbackType.LIKE: "喜欢",
            FeedbackType.DISLIKE: "不喜欢",
        }[self]


class FeedbackReasonType(IntEnum):
    IRRELEVANT = 1
    FACT_OR_DATA_ERROR = 2
    MISUNDERSTANDING = 3
    MISSING_KEY_INFO = 4
    UNCLEAR_EXPRESSION = 5
    TOO_SLOW = 6
    OTHER = 7

    @property
    def label(self) -> str:
        return {
            FeedbackReasonType.IRRELEVANT: "答非所问",
            FeedbackReasonType.FACT_OR_DATA_ERROR: "事实或数据错误",
            FeedbackReasonType.MISUNDERSTANDING: "理解错误",
            FeedbackReasonType.MISSING_KEY_INFO: "遗漏关键信息",
            FeedbackReasonType.UNCLEAR_EXPRESSION: "表达不清",
            FeedbackReasonType.TOO_SLOW: "响应过慢",
            FeedbackReasonType.OTHER: "其他",
        }[self]


def feedback_type_label(value: int) -> str:
    return FeedbackType(value).label


def feedback_reason_type_label(value: int | None) -> str | None:
    if value is None:
        return None
    return FeedbackReasonType(value).label
