class AgentError(Exception):
    pass


class ToolMatchError(AgentError):
    pass


class ToolExecutionError(AgentError):
    pass
