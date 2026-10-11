class StackEmptyError(IndexError):
    """Raised when pop() or peek() is called on an empty stack.

    It inherits from IndexError, so code that already expects an IndexError
    (the error a plain Python list raises) will still work.
    """


class Stack:
    """A Last In, First Out (LIFO) stack."""

    def __init__(self):
        # The list that stores the items. Index -1 is the top of the stack.
        self._items = []

    def push(self, item):
        """Add an item to the top of the stack. O(1)."""
        self._items.append(item)

    def pop(self):
        """Remove and return the top item. O(1).

        Raises StackEmptyError if the stack is empty.
        """
        if self.is_empty():
            raise StackEmptyError("pop from an empty stack")
        return self._items.pop()

    def peek(self):
        """Return the top item WITHOUT removing it. O(1).

        Raises StackEmptyError if the stack is empty.
        """
        if self.is_empty():
            raise StackEmptyError("peek at an empty stack")
        return self._items[-1]

    def is_empty(self):
        """Return True if the stack has no items, otherwise False. O(1)."""
        return len(self._items) == 0

    def size(self):
        """Return the number of items on the stack. O(1)."""
        return len(self._items)

    def __len__(self):
        """Allow len(stack) to be used."""
        return self.size()

    def __repr__(self):
        """Show the stack contents from bottom to top (useful for debugging)."""
        return f"Stack(bottom -> top: {self._items})"
