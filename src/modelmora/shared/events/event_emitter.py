from typing import List

from pydantic import BaseModel, Field

from modelmora.shared.events.domain_event import DomainEvent


class EventEmitter(BaseModel):
    """Mixin class to provide event emitting capabilities to domain entities.

    Attributes:
        events (List[DomainEvent]): A list to store emitted domain events.

    Methods:
        emit_event(event: DomainEvent) -> None:
            Adds a domain event to the events list.
        clear_events() -> None:
            Clears all stored domain events.
        release_events() -> List[DomainEvent]:
            Returns a copy of the stored domain events and clears the original list.

    Examples:
        >>> class User(EventEmitter):
        ...     id: str
        ...     name: str
        ...
        ...     def change_name(self, new_name: str):
        ...         self.name = new_name
        ...         event = DomainEvent(
        ...             event_type="UserNameChanged",
        ...             aggregate_id=self.id,
        ...             aggregate_type="User",
        ...             payload={"new_name": new_name},
        ...         )
        ...         self.emit_event(event)
        ...
        >>> user = User(id="123", name="Alice")
        >>> user.change_name("Bob")
        >>> events = user.release_events()
        >>> len(events)
        1
        >>> events[0].event_type
        'UserNameChanged'
    """

    events: List[DomainEvent] = Field(default_factory=list)

    def emit_event(self, event: DomainEvent) -> None:
        self.events.append(event)

    def clear_events(self) -> None:
        self.events.clear()

    def release_events(self) -> List[DomainEvent]:
        released_events = self.events.copy()
        self.clear_events()
        return released_events
