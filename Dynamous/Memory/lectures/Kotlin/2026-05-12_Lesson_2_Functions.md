---
type: lecture
course: Kotlin
source_file: Lesson_2_Functions.pptx
date: 2026-05-12
tags: [lecture, kotlin]
---

# Lesson 2: Functions

## Key concepts
- Functions declared with `fun` keyword; entry point is `main()`
- Almost everything in Kotlin is an expression with a value
- `Unit` is the return type for functions that don't return a meaningful value; declaration is optional
- Default parameters provide fallback values; required parameters must be supplied
- Named arguments improve readability, especially with many parameters
- Single-expression functions can omit braces and use `=` syntax
- Lambdas are unnamed functions that can be stored in variables and passed as arguments
- Higher-order functions take functions as parameters or return functions
- Kotlin functions are first-class: can be stored in variables, passed as arguments, returned from other functions
- List filters (default: eager) apply conditions to select elements; Sequences enable lazy evaluation
- Function references use `::` operator to pass named functions as arguments

## Worked examples

Create a Kotlin file and main function:
```kotlin
fun main(args: Array<String>) {
    println("Hello, world!")
}
```

Use arguments via string templates:
```kotlin
fun main(args: Array<String>) {
    println("Hello, ${args[0]}")
}
```

if expressions have values:
```kotlin
val temperature = 20
val isHot = if (temperature > 40) true else false
println(isHot)
// ⇒ false
```

println() returns Unit:
```kotlin
val isUnit = println("This is an expression")
println(isUnit)
// ⇒ kotlin.Unit
```

Default parameters:
```kotlin
fun drive(speed: String = "fast") {
    println("driving $speed")
}
drive()              // ⇒ driving fast
drive("slow")        // ⇒ driving slowly
drive(speed = "turtle-like")  // ⇒ driving turtle-like
```

Single-expression function:
```kotlin
fun double(x: Int): Int = x * 2
```

Lambda function:
```kotlin
var dirtLevel = 20
val waterFilter = {level: Int -> level / 2}
println(waterFilter(dirtLevel))
// ⇒ 10
```

Function type syntax:
```kotlin
val waterFilter: (Int) -> Int = {level -> level / 2}
```

Higher-order function:
```kotlin
fun encodeMsg(msg: String, encode: (String) -> String): String {
    return encode(msg)
}

val enc1: (String) -> String = { input -> input.toUpperCase() }
println(encodeMsg("abc", enc1))
```

Passing function reference:
```kotlin
fun enc2(input: String): String = input.reversed()
encodeMsg("abc", ::enc2)
```

Last parameter call syntax:
```kotlin
encodeMsg("acronym") { input -> input.toUpperCase() }
```

repeat() using last parameter call syntax:
```kotlin
repeat(3) {
    println("Hello")
}
```

Filter with implicit `it` parameter:
```kotlin
val ints = listOf(1, 2, 3)
ints.filter { it > 0 }
```

Filter example:
```kotlin
val books = listOf("nature", "biology", "birds")
println(books.filter { it[0] == 'b' })
// ⇒ [biology, birds]
```

Eager filter (default):
```kotlin
val instruments = listOf("viola", "cello", "violin")
val eager = instruments.filter { it[0] == 'v' }
println("eager: " + eager)
// ⇒ eager: [viola, violin]
```

Lazy filter using Sequence:
```kotlin
val instruments = listOf("viola", "cello", "violin")
val filtered = instruments.asSequence().filter { it[0] == 'v'}
println("filtered: " + filtered)
// ⇒ filtered: kotlin.sequences.FilteringSequence@386cc1c4
```

Convert Sequence back to List:
```kotlin
val newList = filtered.toList()
println("new list: " + newList)
// ⇒ new list: [viola, violin]
```

map() transformation:
```kotlin
val numbers = setOf(1, 2, 3)
println(numbers.map { it * 3 })
// => [3, 6, 9]
```

flatten() transformation:
```kotlin
val numberSets = listOf(setOf(1, 2, 3), setOf(4, 5), setOf(1, 2))
println(numberSets.flatten())
// => [1, 2, 3, 4, 5, 1, 2]
```

## Study cards

- Q: What keyword declares a function in Kotlin? | A: `fun`

- Q: What is the return type of a function that doesn't return a meaningful value, and is it required to be explicit? | A: `Unit`; explicit declaration is optional

- Q: How do you define a default parameter value in a function? | A: Use `=` after the type: `fun drive(speed: String = "fast")`

- Q: What is a lambda function in Kotlin? | A: An unnamed function expression that can be stored in variables or passed as arguments; syntax is `{parameter -> code}`

- Q: What is a higher-order function? | A: A function that takes another function as a parameter or returns a function

- Q: How do you pass a named function as an argument to another function? | A: Use the `::` operator, e.g., `encodeMsg("abc", ::enc2)`

- Q: What is the difference between eager and lazy filter evaluation? | A: Eager (default) creates a new list immediately; lazy using Sequences defers evaluation until elements are accessed

- Q: How do you convert a Sequence to a List? | A: Use `toList()` method

- Q: In a filter lambda with one parameter, what is the implicit parameter name if not declared? | A: `it`

- Q: What are the two main list transformation functions covered? | A: `map()` (applies same transform to every item) and `flatten()` (flattens nested collections into single list)

## Open questions

- When would lazy evaluation with Sequences be preferred over eager filters in practice?
- How do inline functions differ from regular higher-order functions?
- What are the performance implications of chaining multiple filter, map, and other transformations?
- Can lambdas capture variables from outer scopes, and what are the constraints?
