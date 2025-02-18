class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class MyLinkedList:
    def __init__(self):
        self.head = None
        self.size = 0

    def add_head(self, data):
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node
        self.size += 1

    def remove_head(self):
        if self.is_empty():
            raise Exception("EmptyStackException")
        removed_data = self.head.data
        self.head = self.head.next
        self.size -= 1
        return removed_data

    def get_head(self):
        if self.is_empty():
            raise Exception("EmptyStackException")
        return self.head.data

    def is_empty(self):
        return self.head is None

    def get_size(self):  # Changed from size() to get_size()
        return self.size

    def __str__(self):
        current = self.head
        elements = []
        while current:
            elements.append(current.data)
            current = current.next
        return str(elements)

class MyStackLL:
    def __init__(self):
        self.stack = MyLinkedList()
        self._size = 0  # Initialize _size attribute to 0

    def push(self, element):
        self.stack.add_head(element)
        self._size += 1  # Increment size when pushing

    def pop(self):
        if self.is_empty():
            raise Exception("EmptyStackException")
        removed_data = self.stack.remove_head()
        self._size -= 1  # Decrement size when popping
        return removed_data

    def top(self):
        if self.is_empty():
            raise Exception("EmptyStackException")
        return self.stack.get_head()

    def is_empty(self):
        return self.stack.is_empty()

    def size(self):  # Keep the original method name
        return self._size

    def __str__(self):
        return str(self.stack) 
if __name__ == "main":
    stack = MyStackLL() 
    print(stack.is_empty())
