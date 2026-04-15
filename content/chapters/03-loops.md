# Chapter 3: Loops

Loops repeat a block of code. `for` loops iterate over a sequence; `while` loops run as long as a condition is true.

## Code Examples

### Example 1: for loop over a list

```python
fruits = ["apple", "banana", "cherry"]

for fruit in fruits:
    print(fruit)
```

**Output:**
```
apple
banana
cherry
```

### Example 2: for loop with range

```python
for i in range(1, 6):
    print(i * i)
```

**Output:**
```
1
4
9
16
25
```

### Example 3: while loop

```python
count = 3

while count > 0:
    print(f"Countdown: {count}")
    count -= 1

print("Go!")
```

**Output:**
```
Countdown: 3
Countdown: 2
Countdown: 1
Go!
```
