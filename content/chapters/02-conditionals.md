# Chapter 2: Conditionals

Conditionals let your program make decisions. Use `if`, `elif`, and `else` to run different code depending on whether a condition is true or false.

## Code Examples

### Example 1: Basic if/else

```python
temperature = 30

if temperature > 25:
    print("It's hot outside.")
else:
    print("It's not too hot.")
```

**Output:**
```
It's hot outside.
```

### Example 2: elif chain

```python
grade = 78

if grade >= 90:
    print("A")
elif grade >= 80:
    print("B")
elif grade >= 70:
    print("C")
else:
    print("F")
```

**Output:**
```
C
```

### Example 3: Combining conditions

```python
is_raining = True
has_umbrella = False

if is_raining and not has_umbrella:
    print("You'll get wet!")
elif is_raining and has_umbrella:
    print("You're prepared.")
else:
    print("No rain today.")
```

**Output:**
```
You'll get wet!
```
