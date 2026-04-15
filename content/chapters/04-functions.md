# Chapter 4: Functions

Functions let you name and reuse a block of code. Define one with `def`, give it parameters, and call it whenever you need it.

## Code Examples

### Example 1: Defining and calling a function

```python
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")
greet("Bob")
```

**Output:**
```
Hello, Alice!
Hello, Bob!
```

### Example 2: Function with a return value

```python
def add(a, b):
    return a + b

result = add(3, 7)
print(result)
```

**Output:**
```
10
```

### Example 3: Default parameters

```python
def power(base, exponent=2):
    return base ** exponent

print(power(3))
print(power(2, 10))
```

**Output:**
```
9
1024
```
