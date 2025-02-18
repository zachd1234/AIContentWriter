from sorting import Sorting  # Import the Sorting class
from my_stack_ll import MyStackLL  # Import the MyStackLL class

def main():
    # Example array for sorting
    arr = [64, 34, 25, 12, 22, 11, 90]

    # Calling sorting methods
    print("Original array:", arr)
    
    # Bubble Sort
    bubble_sorted = arr.copy()  # Copy the array to preserve the original
    Sorting.bubble_sort(bubble_sorted)
    print("Bubble sorted array:", bubble_sorted)

    # Selection Sort
    selection_sorted = arr.copy()
    Sorting.selection_sort(selection_sorted)
    print("Selection sorted array:", selection_sorted)

    # Insertion Sort
    insertion_sorted = arr.copy()
    Sorting.insertion_sort(insertion_sorted)
    print("Insertion sorted array:", insertion_sorted)

    # Merge Sort
    merge_sorted = arr.copy()
    Sorting.merge_sort(merge_sorted)
    print("Merge sorted array:", merge_sorted)

    # Quick Sort
    quick_sorted = arr.copy()
    Sorting.quick_sort(quick_sorted)
    print("Quick sorted array:", quick_sorted)

    # Example usage of MyStackLL
    stack = MyStackLL()
    print("\nStack operations:")
    
    # Pushing elements onto the stack
    stack.push(10)
    stack.push(20)
    stack.push(30)
    print("Stack after pushes:", stack)

    # Popping an element from the stack
    popped_element = stack.pop()
    print("Popped element:", popped_element)
    print("Stack after pop:", stack)

    # Checking the top element
    top_element = stack.top()
    print("Top element:", top_element)

    # Checking if the stack is empty
    is_empty = stack.is_empty()
    print("Is stack empty?", is_empty)

    # Getting the size of the stack
    size = stack.get_size()
    print("Size of stack:", size)

if __name__ == "__main__":
    main()
