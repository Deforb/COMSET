from enum import Enum, auto

class AgentAction:
    """
    Represents an action that an agent can take.
    """

    class Type(Enum):
        NONE = auto()
        ASSIGN = auto()
        ABORT = auto()

    def __init__(
        self,
        agent_id: int = -1,
        res_id: int = -1,
        type_: Type = Type.NONE
    ) -> None:
        """
        Private constructor. Use class methods to create instances.
        """
        self.agent_id = agent_id
        self.res_id = res_id
        self.type = type_

    @classmethod
    def assign_to(cls, agent_id: int, res_id: int) -> 'AgentAction':
        """
        Assigns an agent to a resource.
        """
        return cls(agent_id, res_id, cls.Type.ASSIGN)

    @classmethod
    def do_nothing(cls) -> 'AgentAction':
        """
        Creates an action representing no operation.
        """
        return cls()

    @classmethod
    def abort(cls, agent_id: int) -> 'AgentAction':
        """
        Aborts the current assignment of an agent.
        """
        return cls(agent_id=agent_id, type_=cls.Type.ABORT)

    def get_type(self) -> 'AgentAction.Type':
        """
        Returns the type of this action.
        """
        return self.type