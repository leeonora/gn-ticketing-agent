def calculate_average(numbers):
    return sum(numbers) / len(numbers)

# has deliberate problem, i.e. calling the function with an empty list raises ZeroDivisionError.