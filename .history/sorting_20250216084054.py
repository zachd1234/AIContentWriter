class Sorting:
    comparison = 0
    assignment = 0

    @staticmethod
    def bubble_sort(arr):
        Sorting.comparison = 0
        Sorting.assignment = 0
        
        for i in range(len(arr)):
            for k in range(len(arr) - 1 - i):
                Sorting.comparison += 1
                if arr[k] > arr[k + 1]:
                    arr[k], arr[k + 1] = arr[k + 1], arr[k]  # Swap
                    Sorting.assignment += 3
        
        print(f", {Sorting.comparison}, {Sorting.assignment}")

    @staticmethod
    def selection_sort(arr):
        Sorting.comparison = 0
        Sorting.assignment = 0
        
        for i in range(len(arr)):
            min_index = i
            for k in range(i + 1, len(arr)):
                Sorting.comparison += 1
                if arr[k] < arr[min_index]:
                    min_index = k
                    Sorting.assignment += 2
            
            arr[i], arr[min_index] = arr[min_index], arr[i]  # Swap
            Sorting.assignment += 3
        
        print(f", {Sorting.comparison}, {Sorting.assignment}")

    @staticmethod
    def insertion_sort(arr):
        Sorting.comparison = 0
        Sorting.assignment = 0
        
        for i in range(1, len(arr)):
            insrt_value = arr[i]
            k = i - 1
            
            Sorting.comparison += 1
            while k >= 0 and insrt_value < arr[k]:
                arr[k + 1] = arr[k]
                k -= 1
                Sorting.assignment += 1
                Sorting.comparison += 1
            
            arr[k + 1] = insrt_value
            Sorting.assignment += 1
        
        print(f", {Sorting.comparison}, {Sorting.assignment}")

    @staticmethod
    def merge_sort(arr):
        Sorting.comparison = 0
        Sorting.assignment = 0
        
        Sorting._merge_sort(arr, 0, len(arr) - 1)
        print(f", {Sorting.comparison}, {Sorting.assignment}")

    @staticmethod
    def _merge_sort(arr, beg, end):
        Sorting.comparison += 1
        if beg < end:
            mid = (beg + end) // 2
            Sorting._merge_sort(arr, beg, mid)
            Sorting._merge_sort(arr, mid + 1, end)
            Sorting.merge(arr, beg, mid, end)
            Sorting.assignment += 4

    @staticmethod
    def merge(arr, beg, mid, end):
        temp = arr[beg:end + 1]
        left_cur = beg
        right_cur = mid + 1
        temp_cur = 0
        
        while left_cur <= mid and right_cur <= end:
            Sorting.comparison += 1
            if arr[left_cur] < arr[right_cur]:
                temp[temp_cur] = arr[left_cur]
                left_cur += 1
            else:
                temp[temp_cur] = arr[right_cur]
                right_cur += 1
            temp_cur += 1
            Sorting.assignment += 1
        
        while left_cur <= mid:
            temp[temp_cur] = arr[left_cur]
            left_cur += 1
            temp_cur += 1
            Sorting.assignment += 1
        
        while right_cur <= end:
            temp[temp_cur] = arr[right_cur]
            right_cur += 1
            temp_cur += 1
            Sorting.assignment += 1
        
        for k in range(len(temp)):
            arr[beg + k] = temp[k]
            Sorting.assignment += 1

    @staticmethod
    def quick_sort(arr):
        Sorting.comparison = 0
        Sorting.assignment = 0
        
        Sorting._quick_sort(arr, 0, len(arr) - 1)
        print(f", {Sorting.comparison}, {Sorting.assignment}")

    @staticmethod
    def _quick_sort(arr, beg, end):
        Sorting.comparison += 1
        if beg < end:
            pivot_index = Sorting.partition(arr, beg, end)
            Sorting._quick_sort(arr, beg, pivot_index - 1)
            Sorting._quick_sort(arr, pivot_index + 1, end)
            Sorting.assignment += 3

    @staticmethod
    def partition(arr, beg, end):
        pivot_index = beg + (end - beg) // 2
        arr[end], arr[pivot_index] = arr[pivot_index], arr[end]  # Swap pivot to end
        pivot_val = arr[end]
        left_cur = beg
        right_cur = end - 1
        
        while True:
            while left_cur <= right_cur and arr[left_cur] < pivot_val:
                left_cur += 1
                Sorting.comparison += 1
            
            while right_cur >= left_cur and arr[right_cur] > pivot_val:
                right_cur -= 1
                Sorting.comparison += 1
            
            if left_cur >= right_cur:
                break
            
            arr[left_cur], arr[right_cur] = arr[right_cur], arr[left_cur]  # Swap
            Sorting.assignment += 3
        
        arr[left_cur], arr[end] = arr[end], arr[left_cur]  # Swap pivot back
        Sorting.assignment += 3
        
        return left_cur 