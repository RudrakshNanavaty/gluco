"""Which tools each role gets, bound to that user's scope."""

from collections.abc import Callable

from agents import FunctionTool

from agent.auth import Role
from agent.query import QueryService
from agent.tools import clinician, patient

TOOLS: dict[Role, Callable[[QueryService], list[FunctionTool]]] = {
    "clinician": clinician.build,
    "patient": patient.build,
}
