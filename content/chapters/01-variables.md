# Chapter 1: Variables and Data Types

Variables store values so you can use them later. In Python, you assign a value with `=`. Python figures out the type automatically.

## Code Examples

### Example 1: Assigning variables

```python
name = "Alice"
age = 25
height = 1.68

print(name)
print(age)
print(height)
```

**Output:**
```
Alice
25
1.68
```

### Example 2: Checking types

```python
x = 42
y = 3.14
z = "hello"

print(type(x))
print(type(y))
print(type(z))
```

**Output:**
```
<class 'int'>
<class 'float'>
<class 'str'>
```

### Example 3: Updating a variable

```python
score = 0
print(score)

score = score + 10
print(score)

score += 5
print(score)
```

**Output:**
```
0
10
15
```
