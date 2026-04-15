# Chapter 5: File I/O

Python can read from and write to files using the built-in `open()` function. Always use a `with` block so the file is closed automatically.

## Code Examples

### Example 1: Writing to a file

```python
with open("notes.txt", "w") as f:
    f.write("First line\n")
    f.write("Second line\n")

print("File written.")
```

**Output:**
```
File written.
```

### Example 2: Reading a file line by line

```python
# Assumes notes.txt exists from Example 1
with open("notes.txt", "r") as f:
    for line in f:
        print(line.strip())
```

**Output:**
```
First line
Second line
```

### Example 3: Appending to a file

```python
with open("notes.txt", "a") as f:
    f.write("Third line\n")

with open("notes.txt", "r") as f:
    print(f.read())
```

**Output:**
```
First line
Second line
Third line
```
