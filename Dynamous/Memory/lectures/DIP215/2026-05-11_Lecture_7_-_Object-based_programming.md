---
type: lecture
course: DIP215
source_file: Lecture_7_-_Object-based_programming.pptx
date: 2026-05-11
tags: [lecture, DIP215]
---

# Lecture 7: Object-Based Programming - Class Providers

## Key concepts
- A class is a template; an object is an instance of a class
- Objects encapsulate data (attributes) and behavior (methods)
- Instance variables should be declared private to hide implementation details
- Constructors initialize new objects
- Getters (readers) and setters (writers) provide controlled access to private data
- Standard methods: constructor, getters, setters, toString
- Custom methods implement class-specific functionality (e.g., topUp, makeCall)
- Avoid system-specific code (like System.out.println) in class providers
- Each object instance has its own separate attribute values

## Worked examples

Default constructor for PhoneCard:
```java
public class PhoneCard {
    private String phoneNumber;
    private double balance;
    
    public PhoneCard() {
        phoneNumber = "";
        balance = 0.0;
    }
}
```

Constructor with arguments:
```java
public PhoneCard(String inNumber, double inBalance) {
    phoneNumber = inNumber;
    if (inBalance > 0)
        balance = inBalance;
    else
        balance = 0.0;
}
```

Getter methods:
```java
public String getPhoneNumber() {
    return phoneNumber;
}

public double getBalance() {
    return balance;
}
```

Setter methods:
```java
public void setPhoneNumber(String newNumber) {
    phoneNumber = newNumber;
}

public void setBalance(double newBalance) {
    if (newBalance > 0)
        balance = newBalance;
}
```

toString query method:
```java
public String toString() {
    return phoneNumber + " has balance of " + balance;
}
```

topUp custom method:
```java
public void topUp(double amount) {
    if (amount > 0)
        balance += amount;
}
```

makeCall custom method:
```java
public boolean makeCall(double duration, double costPerMin) {
    double cost = duration * costPerMin;
    if (cost > 0)
        balance -= cost;
    else
        return false;
    if (balance < 0) {
        balance = 0;
        return false;
    }
    return true;
}
```

Creating and invoking objects:
```java
PhoneCard myCard = new PhoneCard("012-1122334", 20);
PhoneCard extraCard = new PhoneCard("012-1234567", 10);
System.out.println(extraCard.getBalance());
```

## Study cards
- Q: What is the difference between a class and an object? | A: A class is a template or blueprint for creating objects; an object is a specific instance of that class with its own data values.
- Q: Why are instance variables declared private? | A: To encapsulate data and hide implementation details, preventing direct access from outside the class and maintaining object integrity.
- Q: What are the four standard methods in a class provider? | A: Constructor, getter (reader), setter (writer), and toString (query).
- Q: What is the difference between a default constructor and a parameterized constructor? | A: A default constructor takes no arguments and sets attributes to default values; a parameterized constructor accepts arguments to initialize attributes to specific values.
- Q: What do getter methods do and why are they needed? | A: Getter methods return the values of private instance variables, allowing controlled read-only access to object data without modifying it.
- Q: What is the purpose of setter methods? | A: Setter methods allow controlled modification of private instance variables, often with validation (e.g., checking for negative values).
- Q: What should a toString method return? | A: A String containing information about the object's current data in a human-readable format.
- Q: Give an example of a custom method from the PhoneCard class and explain its purpose. | A: topUp(double amount) increases the card's balance by the given amount if it is positive; makeCall(double duration, double costPerMin) deducts call cost from balance and returns success/failure.
- Q: Why should we avoid using System.out.println() in class providers? | A: System.out.println() is system-specific and only works for console output; it prevents the class from being reused in GUI applications or applets. Reader/query methods should be used instead.
- Q: How do you create a new object and invoke a method on it? | A: Use the new keyword with the constructor (e.g., PhoneCard myCard = new PhoneCard("012-1122334", 20);) then invoke methods using dot notation (e.g., myCard.topUp(10);).

## Open questions
- How does method overloading work with constructors?
- What are other access modifiers beyond private and public (e.g., protected, package-private)?
- How do we determine which methods and attributes a class should have?
- What is the relationship between class inheritance and method overriding?
- How do we handle errors or invalid states in custom methods?

<!-- related:begin -->
## Related
- [[2026-05-11_Lecture_3_-_Selection_Constructs]]
- [[2026-05-11_Lecture_4_-_Iteration]]
- [[2026-05-11_Lecture_5_-_Static_methods]]
- [[2026-05-11_Lecture_6_-_Object_Oriented_Programming]]
<!-- related:end -->
