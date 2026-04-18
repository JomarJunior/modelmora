from typing import Callable, Dict, List

from pydantic import BaseModel

from modelmora.shared.events.domain_event import DomainEvent

Subscriber = Callable[[DomainEvent], None]


class EventDispatcher(BaseModel):
    """
    EventDispatcher is responsible for managing and dispatching domain events to their respective subscribers.

    Attributes:
        subscribers (Dict[type[DomainEvent], List[Subscriber]]): A mapping of domain event
        types to their list of subscribers.

    Methods:
        register_subscribers(subscribers: Dict[type[DomainEvent], List[Subscriber]]) -> None:
            Registers subscribers for specific domain event types.
        dispatch_all(events: List[DomainEvent]) -> None:
            Dispatches a list of domain events to their respective subscribers.

    Examples:
        >>> def handle_user_created(event: DomainEvent):
        ...     print(f"User created with ID: {event.payload['user_id']}")
        ...
        >>> dispatcher = EventDispatcher()
        >>> dispatcher.register_subscribers({
        ...     UserCreatedEvent: [handle_user_created],
        ... })
        >>> event = UserCreatedEvent(
        ...     event_type="UserCreated",
        ...     aggregate_id="123",
        ...     aggregate_type="User",
        ...     payload={"user_id": "123"},
        ... )
        >>> dispatcher.dispatch_all([event])
        User created with ID: 123
    """

    subscribers: Dict[type[DomainEvent], List[Subscriber]] = {}

    def register_subscribers(
        self,
        subscribers: Dict[type[DomainEvent], List[Subscriber]],
    ) -> None:
        for event_type, subs in subscribers.items():
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].extend(subs)

    def dispatch_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            event_type = type(event)
            if event_type in self.subscribers:
                for subscriber in self.subscribers[event_type]:
                    subscriber(event)
