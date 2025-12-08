# Clean Code Review Checklist

This checklist provides a set of rules to verify during code review to ensure code quality, readability, and maintainability.

## 1. Naming

- [ ] **Clarity**: Are names descriptive and unambiguous? (e.g., `elapsedTimeInDays` instead of `d`).
- [ ] **Searchability**: Are names easy to search for? Avoid single-letter names and magic numbers.
- [ ] **No Encodings**: Verify that names do not contain type or scope prefixes (e.g., `m_`, `str`).
- [ ] **Consistency**: Is the same term used for the same concept across different classes? (e.g., consistently use `get` instead of a mix of `get`, `fetch`, and `retrieve`).

## 2. Functions and Methods

- [ ] **Single Responsibility**: Does each method do only one thing?
- [ ] **Size**: Are methods small (ideally under 25 lines)?
- [ ] **Argument Count**: Do methods have five or fewer arguments? If more, should a parameter object be used instead?
- [ ] **No Side Effects**: Does the method do only what its name implies, without unexpected side effects?
- [ ] **DRY Principle**: Is there any duplicate code that should be extracted into a shared method?

## 3. Documentation and Comments

- [ ] **Self-Documenting Code**: Is the code clear enough on its own? If a comment is needed to explain complex code, should the code be refactored instead?
- [ ] **Javadoc for Public APIs**: Verify that all `public` classes and methods have Javadoc.
- [ ] **Author Tag**: For new files, confirm that the class Javadoc contains an `@author` and `@since` tag.
- [ ] **No Redundant Comments**: Check for comments that merely state what the code is doing (e.g., `// increment i`).
- [ ] **No Commented-Out Code**: Ensure there is no dead code commented out. It should be deleted.

## 4. Formatting and Layout

- [ ] **File Structure**:
    - [ ] Is there a blank line between the `package` and `import` statements, before the class definition?
    - [ ] Does the class start with a single empty line?
    - [ ] Does the file end with a single empty line?
- [ ] **Method Order**:
    - [ ] Are all `public` methods grouped together?
    - [ ] Are all `private` methods grouped together *after* the public methods?
- [ ] **Readability**:
    - [ ] Is there a blank line before `return` statements?
    - [ ] Are blank lines used effectively to separate logical blocks of code?
- [ ] **Line Length**: Are lines kept to a reasonable length (e.g., under 120 characters) to prevent horizontal scrolling?

## 5. Error Handling

- [ ] **Specific Exceptions**: Are specific, checked exceptions used instead of generic `Exception`?
- [ ] **No Swallowed Exceptions**: Verify that `catch` blocks are not empty. Exceptions must be handled, logged, or re-thrown.
- [ ] **Contextual Information**: When an exception is caught and re-thrown, is useful context added to the new exception?

## 6. General Design

- [ ] **Simplicity (KISS)**: Is the solution overly complex? Is there a simpler way to achieve the same result?
- [ ] **No Unnecessary Features (YAGNI)**: Is the code implementing functionality that isn't required by the current scope?
