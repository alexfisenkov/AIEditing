"""The one error of a pipeline: the message is for a human."""


class PipelineError(RuntimeError):
    """The profile asks for something the pipeline cannot do, or a step failed."""
