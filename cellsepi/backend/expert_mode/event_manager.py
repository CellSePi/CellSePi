from typing import List, Type


class EventManager:
    """
    Manages the different Listeners and notify them if they associated event happens.
    """
    def __init__(self):
        self._listeners: dict[Type[Event], List[EventListener]] = {}

    def subscribe(self, listener: EventListener):
        """
        Adds a listener to the event manager.
        """
        event_type = listener.get_event_type()
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, listener: EventListener):
        """
        Removes a listener from the event manager.
        """
        event_type = listener.get_event_type()
        if event_type not in self._listeners or listener not in self._listeners[event_type]:
            raise ValueError("Listener is not subscribed")
        self._listeners[event_type].remove(listener)
        if len(self._listeners[event_type]) == 0:
            del self._listeners[event_type]

    def notify(self,event: Event):
        """
        Notify all listeners associated with the given event.
        """
        event_type = type(event)
        if event_type not in self._listeners:
            return
        for listener in self._listeners.get(event_type, []):
            listener.update(event)