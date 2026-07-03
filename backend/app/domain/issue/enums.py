from enum import IntEnum


class IssueProcessStatus(IntEnum):
    PENDING = 1
    ANALYZING = 2
    LOCATED = 3
    FIXED = 4
    IGNORED = 5
    CLOSED = 6

    @property
    def label(self) -> str:
        return {
            IssueProcessStatus.PENDING: "待处理",
            IssueProcessStatus.ANALYZING: "分析中",
            IssueProcessStatus.LOCATED: "已定位",
            IssueProcessStatus.FIXED: "已修复",
            IssueProcessStatus.IGNORED: "忽略",
            IssueProcessStatus.CLOSED: "关闭",
        }[self]


class IssuePriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

    @property
    def label(self) -> str:
        return {
            IssuePriority.LOW: "低",
            IssuePriority.MEDIUM: "中",
            IssuePriority.HIGH: "高",
            IssuePriority.URGENT: "紧急",
        }[self]


class IssueRootCauseType(IntEnum):
    PROMPT = 1
    MODEL_CAPABILITY = 2
    CONTEXT = 3
    TOOL_SELECTION = 4
    TOOL_DATA = 5
    BUSINESS_RULE = 6
    FRONTEND_DISPLAY = 7
    SYSTEM_EXCEPTION = 8
    UNCLEAR_INPUT = 9
    OTHER = 10

    @property
    def label(self) -> str:
        return {
            IssueRootCauseType.PROMPT: "Prompt 问题",
            IssueRootCauseType.MODEL_CAPABILITY: "模型能力问题",
            IssueRootCauseType.CONTEXT: "上下文问题",
            IssueRootCauseType.TOOL_SELECTION: "工具选择问题",
            IssueRootCauseType.TOOL_DATA: "工具数据问题",
            IssueRootCauseType.BUSINESS_RULE: "业务规则问题",
            IssueRootCauseType.FRONTEND_DISPLAY: "前端展示问题",
            IssueRootCauseType.SYSTEM_EXCEPTION: "系统异常",
            IssueRootCauseType.UNCLEAR_INPUT: "用户输入不明确",
            IssueRootCauseType.OTHER: "其他",
        }[self]


def issue_status_label(value: int | None) -> str | None:
    if value is None:
        return None
    return IssueProcessStatus(value).label


def issue_priority_label(value: int | None) -> str | None:
    if value is None:
        return None
    return IssuePriority(value).label


def issue_root_cause_type_label(value: int | None) -> str | None:
    if value is None:
        return None
    return IssueRootCauseType(value).label
